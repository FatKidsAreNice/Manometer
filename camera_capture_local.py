#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CameraConfig:
    camera_id: str
    device_path: str
    width: int
    height: int
    input_format: str


@dataclass(frozen=True)
class CaptureConfig:
    output_dir: Path
    interval_seconds: int


class LocalCameraCaptureService:
    def __init__(self, cameras: list[CameraConfig], config: CaptureConfig):
        self.cameras = cameras
        self.config = config

    def run_forever(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        while True:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for camera in self.cameras:
                self._capture_image(camera, timestamp)

            self._print_power_status()
            time.sleep(self.config.interval_seconds)

    def _capture_image(self, camera: CameraConfig, timestamp: str) -> None:
        camera_dir = self.config.output_dir / camera.camera_id
        camera_dir.mkdir(parents=True, exist_ok=True)

        final_path = camera_dir / f"{camera.camera_id}_{timestamp}.jpg"
        temp_path = camera_dir / f".{camera.camera_id}_{timestamp}.tmp.jpg"

        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "v4l2",
            "-input_format",
            camera.input_format,
            "-video_size",
            f"{camera.width}x{camera.height}",
            "-i",
            camera.device_path,
            "-frames:v",
            "1",
            str(temp_path),
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[FEHLER] Aufnahme fehlgeschlagen: {camera.camera_id}")
            print(result.stderr.strip())

            if temp_path.exists():
                temp_path.unlink()

            return

        temp_path.rename(final_path)
        print(f"[OK] Bild gespeichert: {final_path}")

    def _print_power_status(self) -> None:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"[PI] {result.stdout.strip()}")


def main() -> int:
    cameras = [
        CameraConfig(
            camera_id="hd_webcam",
            device_path="/dev/v4l/by-id/usb-HD_Web_Camera_HD_Web_Camera_Ucamera001-video-index0",
            width=1920,
            height=1080,
            input_format="mjpeg",
        ),
        CameraConfig(
            camera_id="sonix_webcam",
            device_path="/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._1080P_FHD_Camera_SN0001-video-index0",
            width=1920,
            height=1080,
            input_format="mjpeg",
        ),
    ]

    config = CaptureConfig(
        output_dir=Path("/home/pi/camera_upload_buffer"),
        interval_seconds=5,
    )

    service = LocalCameraCaptureService(cameras=cameras, config=config)
    service.run_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
