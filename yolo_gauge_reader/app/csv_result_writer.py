import csv
from pathlib import Path

from app.models import ReadingResult


class CsvResultWriter:
    FIELDNAMES = [
        "image_path",
        "profile_id",
        "profile_name",
        "value",
        "unit",
        "needle_angle_deg",
        "mapping_mode",
        "status",
        "message",
        "gauge_confidence",
        "center_confidence",
        "tip_confidence",
        "min_confidence",
        "max_confidence",
        "overlay_path",
    ]

    def write(self, output_path: Path, results: list[ReadingResult]) -> None:
        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()

            for result in results:
                writer.writerow(
                    {
                        "image_path": str(result.image_path),
                        "profile_id": result.profile_id,
                        "profile_name": result.profile_name,
                        "value": "" if result.value is None else f"{result.value:.6f}",
                        "unit": result.unit,
                        "needle_angle_deg": "" if result.needle_angle_deg is None else f"{result.needle_angle_deg:.6f}",
                        "mapping_mode": result.mapping_mode,
                        "status": result.status,
                        "message": result.message,
                        "gauge_confidence": self._format_optional(result.gauge_confidence),
                        "center_confidence": self._format_optional(result.center_confidence),
                        "tip_confidence": self._format_optional(result.tip_confidence),
                        "min_confidence": self._format_optional(result.min_confidence),
                        "max_confidence": self._format_optional(result.max_confidence),
                        "overlay_path": "" if result.overlay_path is None else str(result.overlay_path),
                    }
                )

    def _format_optional(self, value: float | None) -> str:
        if value is None:
            return ""

        return f"{value:.6f}"
