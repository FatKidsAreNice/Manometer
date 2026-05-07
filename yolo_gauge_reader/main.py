import argparse
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Liest Manometerbilder mit zweistufiger YOLO-Erkennung aus.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stage1-model", required=True, type=Path)
    parser.add_argument("--stage2-model", required=True, type=Path)
    parser.add_argument("--stage1-imgsz", default=640, type=int)
    parser.add_argument("--stage2-imgsz", default=960, type=int)
    parser.add_argument("--stage1-conf", default=0.25, type=float)
    parser.add_argument("--stage2-conf", default=0.10, type=float)
    parser.add_argument("--crop-padding", default=1.30, type=float)
    parser.add_argument("--mapping-mode", choices=["auto", "profile", "detected_minmax"], default="auto")
    parser.add_argument("--max-images-per-folder", default=0, type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    reader = TwoStageGaugeReader(
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
        max_images_per_folder=args.max_images_per_folder,
    )

    results = reader.run(args.input, args.output)
    ok_count = sum(1 for result in results if result.status == "ok")
    review_count = sum(1 for result in results if result.status != "ok")

    print(f"Fertig. Bilder: {len(results)} | ok: {ok_count} | prüfen: {review_count}")
    print(f"CSV: {args.output.expanduser().resolve() / 'readings.csv'}")
    print(f"Overlays: {args.output.expanduser().resolve() / 'overlays'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
