from pathlib import Path

from PIL import Image, ImageDraw

from app.models import CropInfo, Detection, GaugeProfile, ReadingResult, Stage2Points


class OverlayRenderer:
    def render(
        self,
        image: Image.Image,
        output_path: Path,
        profile: GaugeProfile,
        result: ReadingResult,
        gauge_detection: Detection | None,
        crop_info: CropInfo | None,
        points: Stage2Points | None,
    ) -> None:
        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        overlay = image.copy()
        draw = ImageDraw.Draw(overlay)

        if gauge_detection is not None:
            draw.rectangle(
                (gauge_detection.x1, gauge_detection.y1, gauge_detection.x2, gauge_detection.y2),
                outline="yellow",
                width=3,
            )
            draw.text(
                (gauge_detection.x1 + 4, gauge_detection.y1 + 4),
                f"gauge {gauge_detection.confidence:.2f}",
                fill="yellow",
            )

        if crop_info is not None:
            draw.rectangle((crop_info.x1, crop_info.y1, crop_info.x2, crop_info.y2), outline="orange", width=3)

        if points is not None:
            self._draw_points(draw, points)

        self._draw_text_block(draw, profile, result)
        overlay.save(output_path, quality=95)

    def _draw_points(self, draw: ImageDraw.ImageDraw, points: Stage2Points) -> None:
        if points.center is not None:
            self._draw_cross(draw, points.center.x, points.center.y, "lime", "center")

        if points.tip is not None:
            self._draw_cross(draw, points.tip.x, points.tip.y, "cyan", "tip")

        if points.min_point is not None:
            self._draw_cross(draw, points.min_point.x, points.min_point.y, "white", "min")

        if points.max_point is not None:
            self._draw_cross(draw, points.max_point.x, points.max_point.y, "magenta", "max")

        if points.center is not None and points.tip is not None:
            draw.line((points.center.x, points.center.y, points.tip.x, points.tip.y), fill="cyan", width=3)

    def _draw_cross(self, draw: ImageDraw.ImageDraw, x: float, y: float, color: str, label: str) -> None:
        size = 8
        draw.line((x - size, y, x + size, y), fill=color, width=3)
        draw.line((x, y - size, x, y + size), fill=color, width=3)
        draw.text((x + 10, y - 10), label, fill=color)

    def _draw_text_block(self, draw: ImageDraw.ImageDraw, profile: GaugeProfile, result: ReadingResult) -> None:
        value_text = "n/a" if result.value is None else f"{result.value:.3f} {result.unit}"
        angle_text = "n/a" if result.needle_angle_deg is None else f"{result.needle_angle_deg:.2f} deg"

        lines = [
            f"profile: {profile.display_name}",
            f"value: {value_text}",
            f"angle: {angle_text}",
            f"status: {result.status}",
            f"mapping: {result.mapping_mode}",
            f"msg: {result.message}",
        ]

        x = 20
        y = 20
        line_height = 18
        block_width = 650
        block_height = line_height * len(lines) + 12
        draw.rectangle((x - 8, y - 8, x + block_width, y + block_height), fill="black")

        for index, line in enumerate(lines):
            draw.text((x, y + index * line_height), line, fill="white")
