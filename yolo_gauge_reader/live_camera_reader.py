#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.csv_result_writer import CsvResultWriter
from app.detection_selector import DetectionSelector
from app.gauge_cropper import GaugeCropper
from app.image_loader import ImageLoader
from app.image_scanner import ImageScanner
from app.overlay_renderer import OverlayRenderer
from app.profile_repository import ProfileRepository
from app.two_stage_reader import TwoStageGaugeReader
from app.value_mapper import GaugeValueMapper
from app.yolo_predictor import YoloPredictor


@dataclass(frozen=True)
class CameraProfileConfig:
    camera_id: str
    upload_dir: Path
    profile_path: Path


@dataclass(frozen=True)
class LiveReaderConfig:
    camera_profiles: list[CameraProfileConfig]
    output_dir: Path
    work_dir: Path
    interval_seconds: int
    max_images_per_camera: int
    once: bool


class CameraProfileConfigRepository:
    def load(self, config_path: Path) -> list[CameraProfileConfig]:
        config_path = config_path.expanduser().resolve()

        if not config_path.exists():
            raise FileNotFoundError(f"Kamera-Konfiguration nicht gefunden: {config_path}")

        with config_path.open("r", encoding="utf-8") as file:
            raw_config = json.load(file)

        cameras = raw_config.get("cameras", [])

        if not isinstance(cameras, list) or not cameras:
            raise ValueError("Die Konfiguration muss eine nicht-leere Liste 'cameras' enthalten.")

        parsed_cameras: list[CameraProfileConfig] = []

        for camera in cameras:
            parsed_cameras.append(
                CameraProfileConfig(
                    camera_id=str(camera["camera_id"]),
                    upload_dir=Path(str(camera["upload_dir"])).expanduser().resolve(),
                    profile_path=Path(str(camera["profile_path"])).expanduser().resolve(),
                )
            )

        return parsed_cameras


class LiveBatchPreparer:
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

    def prepare_batch(self, batch_id: str, config: LiveReaderConfig) -> tuple[Path, dict[Path, Path]]:
        batch_input_dir = config.work_dir / "batches" / batch_id / "input"
        batch_input_dir.mkdir(parents=True, exist_ok=True)
        work_to_archive_path: dict[Path, Path] = {}

        for camera_config in config.camera_profiles:
            upload_images = self._find_upload_images(camera_config.upload_dir)

            if config.max_images_per_camera > 0:
                upload_images = upload_images[: config.max_images_per_camera]

            if not upload_images:
                continue

            if not camera_config.profile_path.exists():
                raise FileNotFoundError(
                    f"Profil fuer Kamera {camera_config.camera_id} nicht gefunden: {camera_config.profile_path}"
                )

            camera_input_dir = batch_input_dir / camera_config.camera_id
            camera_input_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(camera_config.profile_path, camera_input_dir / "gauge_profile.json")

            for upload_image in upload_images:
                target_image = camera_input_dir / upload_image.name
                shutil.move(str(upload_image), str(target_image))
                archive_image = config.output_dir / "archive" / camera_config.camera_id / upload_image.name
                work_to_archive_path[target_image.resolve()] = archive_image.resolve()

        return batch_input_dir, work_to_archive_path

    def has_images(self, batch_input_dir: Path) -> bool:
        for image_path in batch_input_dir.glob("*/*"):
            if image_path.is_file() and image_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                return True
        return False

    def archive_processed_images(self, work_to_archive_path: dict[Path, Path]) -> None:
        for work_image, archive_image in work_to_archive_path.items():
            if not work_image.exists():
                continue
            final_archive_path = self._unique_path(archive_image)
            final_archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(work_image), str(final_archive_path))

    def _find_upload_images(self, upload_dir: Path) -> list[Path]:
        if not upload_dir.exists():
            return []

        images = [
            image_path.resolve()
            for image_path in upload_dir.iterdir()
            if image_path.is_file()
            and image_path.suffix.lower() in self.IMAGE_EXTENSIONS
            and not image_path.name.startswith(".")
        ]
        return sorted(images, key=lambda item: item.name.lower())

    def _unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path

        counter = 1
        while True:
            candidate = path.with_name(f"{path.stem}_{counter:03d}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1


class LiveCsvAppender:
    EXTRA_FIELDNAMES = ["batch_id", "camera_id", "archived_image_path"]

    def append_batch(
        self,
        combined_csv_path: Path,
        batch_id: str,
        batch_csv_path: Path,
        work_to_archive_path: dict[Path, Path],
    ) -> None:
        if not batch_csv_path.exists():
            return

        combined_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with batch_csv_path.open("r", newline="", encoding="utf-8") as source_file:
            reader = csv.DictReader(source_file)
            rows = list(reader)
            if reader.fieldnames is None:
                return
            fieldnames = self.EXTRA_FIELDNAMES + reader.fieldnames

        file_exists = combined_csv_path.exists()

        with combined_csv_path.open("a", newline="", encoding="utf-8") as target_file:
            writer = csv.DictWriter(target_file, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for row in rows:
                work_image_path = Path(row.get("image_path", "")).expanduser().resolve()
                camera_id = work_image_path.parent.name
                archived_path = work_to_archive_path.get(work_image_path)
                enriched_row = {
                    "batch_id": batch_id,
                    "camera_id": camera_id,
                    "archived_image_path": "" if archived_path is None else str(archived_path),
                }
                enriched_row.update(row)
                writer.writerow(enriched_row)


class LiveGaugeReaderService:
    def __init__(self, config: LiveReaderConfig, reader: TwoStageGaugeReader):
        self.config = config
        self.reader = reader
        self.preparer = LiveBatchPreparer()
        self.csv_appender = LiveCsvAppender()

    def run(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.config.work_dir.mkdir(parents=True, exist_ok=True)

        while True:
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_input_dir, work_to_archive_path = self.preparer.prepare_batch(batch_id, self.config)

            if not self.preparer.has_images(batch_input_dir):
                print("[INFO] Keine neuen Bilder gefunden.")
                self._cleanup_empty_batch(batch_input_dir)
                if self.config.once:
                    return
                time.sleep(self.config.interval_seconds)
                continue

            batch_output_dir = self.config.output_dir / "batches" / batch_id
            print(f"[INFO] Verarbeite Batch {batch_id}")
            self.reader.run(batch_input_dir, batch_output_dir)
            self.csv_appender.append_batch(
                combined_csv_path=self.config.output_dir / "live_readings.csv",
                batch_id=batch_id,
                batch_csv_path=batch_output_dir / "readings.csv",
                work_to_archive_path=work_to_archive_path,
            )
            self.preparer.archive_processed_images(work_to_archive_path)
            print(f"[OK] Batch abgeschlossen: {batch_id}")

            if self.config.once:
                return

            time.sleep(self.config.interval_seconds)

    def _cleanup_empty_batch(self, batch_input_dir: Path) -> None:
        batch_dir = batch_input_dir.parent
        if batch_dir.exists():
            shutil.rmtree(batch_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live-Auswertung fuer vom Raspberry Pi abgeholte Kamerabilder.")
    parser.add_argument("--camera-config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stage1-model", required=True, type=Path)
    parser.add_argument("--stage2-model", required=True, type=Path)
    parser.add_argument("--stage1-imgsz", default=640, type=int)
    parser.add_argument("--stage2-imgsz", default=960, type=int)
    parser.add_argument("--stage1-conf", default=0.25, type=float)
    parser.add_argument("--stage2-conf", default=0.10, type=float)
    parser.add_argument("--crop-padding", default=1.30, type=float)
    parser.add_argument("--mapping-mode", choices=["auto", "profile", "detected_minmax"], default="auto")
    parser.add_argument("--interval-seconds", default=5, type=int)
    parser.add_argument("--max-images-per-camera", default=2, type=int)
    parser.add_argument("--work-dir", default=Path("/tmp/yolo_gauge_live_reader"), type=Path)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def create_reader(args: argparse.Namespace) -> TwoStageGaugeReader:
    return TwoStageGaugeReader(
        scanner=ImageScanner(),
        image_loader=ImageLoader(),
        profile_repository=ProfileRepository(),
        stage1_predictor=YoloPredictor(
            model_path=args.stage1_model,
            class_names={0: "center", 1: "gauge", 2: "max", 3: "min", 4: "tip"},
            image_size=args.stage1_imgsz,
            confidence=args.stage1_conf,
        ),
        stage2_predictor=YoloPredictor(
            model_path=args.stage2_model,
            class_names={0: "center", 1: "max", 2: "min", 3: "tip"},
            image_size=args.stage2_imgsz,
            confidence=args.stage2_conf,
        ),
        cropper=GaugeCropper(),
        selector=DetectionSelector(),
        value_mapper=GaugeValueMapper(),
        overlay_renderer=OverlayRenderer(),
        result_writer=CsvResultWriter(),
        crop_padding=args.crop_padding,
        mapping_mode=args.mapping_mode,
        max_images_per_folder=0,
    )


def main() -> int:
    args = parse_args()
    camera_profiles = CameraProfileConfigRepository().load(args.camera_config)
    config = LiveReaderConfig(
        camera_profiles=camera_profiles,
        output_dir=args.output.expanduser().resolve(),
        work_dir=args.work_dir.expanduser().resolve(),
        interval_seconds=args.interval_seconds,
        max_images_per_camera=args.max_images_per_camera,
        once=args.once,
    )
    service = LiveGaugeReaderService(config=config, reader=create_reader(args))
    service.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
