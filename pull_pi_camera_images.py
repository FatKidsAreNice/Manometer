#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PullConfig:
    pi_user: str
    pi_host: str
    pi_source_dir: str
    local_target_dir: Path
    interval_seconds: int
    remove_source_files: bool


class PiCameraPullService:
    def __init__(self, config: PullConfig):
        self.config = config

    def run_forever(self) -> None:
        self.config.local_target_dir.mkdir(parents=True, exist_ok=True)

        while True:
            self._pull_images()
            time.sleep(self.config.interval_seconds)

    def _pull_images(self) -> None:
        source = f"{self.config.pi_user}@{self.config.pi_host}:{self.config.pi_source_dir}/"
        target = str(self.config.local_target_dir) + "/"

        command = [
            "rsync",
            "-az",
            "--partial",
            "--include",
            "*/",
            "--include",
            "*.jpg",
            "--exclude",
            "*",
        ]

        if self.config.remove_source_files:
            command.append("--remove-source-files")

        command.extend([source, target])

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            print("[FEHLER] Pull fehlgeschlagen")
            print(result.stderr.strip())
            return

        print("[OK] Pull abgeschlossen")

    def test_connection(self) -> None:
        command = [
            "ssh",
            f"{self.config.pi_user}@{self.config.pi_host}",
            "echo Verbindung zum Pi OK",
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        print(result.stdout.strip())


def main() -> int:
    config = PullConfig(
        pi_user="pi",
        pi_host="10.10.5.50",
        pi_source_dir="/home/pi/camera_upload_buffer",
        local_target_dir=Path("/home/edv/Desktop/pi_camera_uploads"),
        interval_seconds=5,
        remove_source_files=True,
    )

    service = PiCameraPullService(config=config)
    service.test_connection()
    service.run_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
