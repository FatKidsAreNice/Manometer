from pathlib import Path

from app.angle_math import AngleMath
from app.csv_result_writer import CsvResultWriter
from app.detection_selector import DetectionSelector
from app.gauge_cropper import GaugeCropper
from app.image_loader import ImageLoader
from app.image_scanner import ImageScanner
from app.models import CropInfo, Detection, GaugeProfile, Point2D, ReadingResult, Stage2Points
from app.overlay_renderer import OverlayRenderer
from app.profile_repository import ProfileRepository
from app.value_mapper import GaugeValueMapper
from app.yolo_predictor import YoloPredictor


class TwoStageGaugeReader:
    def __init__(
        self,
        scanner: ImageScanner,
        image_loader: ImageLoader,
        profile_repository: ProfileRepository,
        stage1_predictor: YoloPredictor,
        stage2_predictor: YoloPredictor,
        cropper: GaugeCropper,
        selector: DetectionSelector,
        value_mapper: GaugeValueMapper,
        overlay_renderer: OverlayRenderer,
        result_writer: CsvResultWriter,
        crop_padding: float,
        mapping_mode: str,
        max_images_per_folder: int,
    ):
        self.scanner = scanner
        self.image_loader = image_loader
        self.profile_repository = profile_repository
        self.stage1_predictor = stage1_predictor
        self.stage2_predictor = stage2_predictor
        self.cropper = cropper
        self.selector = selector
        self.value_mapper = value_mapper
        self.overlay_renderer = overlay_renderer
        self.result_writer = result_writer
        self.crop_padding = crop_padding
        self.mapping_mode = mapping_mode
        self.max_images_per_folder = max_images_per_folder

    def run(self, input_dir: Path, output_dir: Path) -> list[ReadingResult]:
        input_dir = input_dir.expanduser().resolve()
        output_dir = output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        results: list[ReadingResult] = []

        for profile_folder in self.scanner.find_profile_folders(input_dir):
            profile = self.profile_repository.load(profile_folder / "gauge_profile.json")
            images = self.scanner.find_images(profile_folder, self.max_images_per_folder)

            for image_path in images:
                result = self._process_image(
                    image_path=image_path,
                    profile=profile,
                    output_dir=output_dir,
                    profile_folder_name=profile_folder.name,
                )
                results.append(result)

                value_text = "" if result.value is None else f"{result.value:.3f} {result.unit}"
                print(f"{result.status}: {image_path.name} -> {value_text}")

        self.result_writer.write(output_dir / "readings.csv", results)
        return results

    def _process_image(
        self,
        image_path: Path,
        profile: GaugeProfile,
        output_dir: Path,
        profile_folder_name: str,
    ) -> ReadingResult:
        image = self.image_loader.load_rgb(image_path)
        gauge_detection: Detection | None = None
        crop_info: CropInfo | None = None
        image_points: Stage2Points | None = None

        try:
            stage1_detections = self.stage1_predictor.predict(image)
            gauge_detection = self.selector.select_gauge(stage1_detections)

            if gauge_detection is None:
                return self._manual_review_result(
                    image=image,
                    image_path=image_path,
                    profile=profile,
                    output_dir=output_dir,
                    profile_folder_name=profile_folder_name,
                    message="Stage 1 hat kein gauge erkannt.",
                    gauge_detection=None,
                    crop_info=None,
                    points=None,
                )

            crop_image, crop_info = self.cropper.crop(image, gauge_detection, self.crop_padding)
            stage2_detections = self.stage2_predictor.predict(crop_image)
            crop_points = self.selector.select_stage2_points(stage2_detections)
            image_points = self._stage2_points_to_image_points(crop_points, crop_info)

            if image_points.center is None:
                return self._manual_review_result(
                    image=image,
                    image_path=image_path,
                    profile=profile,
                    output_dir=output_dir,
                    profile_folder_name=profile_folder_name,
                    message="Stage 2 hat center nicht erkannt.",
                    gauge_detection=gauge_detection,
                    crop_info=crop_info,
                    points=image_points,
                )

            if image_points.tip is None:
                return self._manual_review_result(
                    image=image,
                    image_path=image_path,
                    profile=profile,
                    output_dir=output_dir,
                    profile_folder_name=profile_folder_name,
                    message="Stage 2 hat tip nicht erkannt.",
                    gauge_detection=gauge_detection,
                    crop_info=crop_info,
                    points=image_points,
                )

            needle_angle = AngleMath.calculate_angle_deg(
                image_points.center.x,
                image_points.center.y,
                image_points.tip.x,
                image_points.tip.y,
            )

            value, used_mapping_mode, mapping_message = self.value_mapper.map_value(
                profile=profile,
                needle_angle_deg=needle_angle,
                points=image_points,
                mapping_mode=self.mapping_mode,
            )

            status = "ok" if value is not None else "manual_review"
            message = mapping_message if value is not None else "Wert konnte nicht berechnet werden."

            result = self._result(
                image_path=image_path,
                profile=profile,
                value=value,
                needle_angle_deg=needle_angle,
                mapping_mode=used_mapping_mode,
                status=status,
                message=message,
                gauge_detection=gauge_detection,
                points=image_points,
                overlay_path=self._overlay_path(output_dir, profile_folder_name, image_path),
            )

            self.overlay_renderer.render(
                image=image,
                output_path=result.overlay_path,
                profile=profile,
                result=result,
                gauge_detection=gauge_detection,
                crop_info=crop_info,
                points=image_points,
            )

            return result
        except Exception as error:
            return self._manual_review_result(
                image=image,
                image_path=image_path,
                profile=profile,
                output_dir=output_dir,
                profile_folder_name=profile_folder_name,
                message=f"Fehler: {error}",
                gauge_detection=gauge_detection,
                crop_info=crop_info,
                points=image_points,
            )

    def _manual_review_result(
        self,
        image,
        image_path: Path,
        profile: GaugeProfile,
        output_dir: Path,
        profile_folder_name: str,
        message: str,
        gauge_detection: Detection | None,
        crop_info: CropInfo | None,
        points: Stage2Points | None,
    ) -> ReadingResult:
        result = self._result(
            image_path=image_path,
            profile=profile,
            value=None,
            needle_angle_deg=None,
            mapping_mode=self.mapping_mode,
            status="manual_review",
            message=message,
            gauge_detection=gauge_detection,
            points=points,
            overlay_path=self._overlay_path(output_dir, profile_folder_name, image_path),
        )

        self.overlay_renderer.render(
            image=image,
            output_path=result.overlay_path,
            profile=profile,
            result=result,
            gauge_detection=gauge_detection,
            crop_info=crop_info,
            points=points,
        )

        return result

    def _result(
        self,
        image_path: Path,
        profile: GaugeProfile,
        value: float | None,
        needle_angle_deg: float | None,
        mapping_mode: str,
        status: str,
        message: str,
        gauge_detection: Detection | None,
        points: Stage2Points | None,
        overlay_path: Path | None,
    ) -> ReadingResult:
        return ReadingResult(
            image_path=image_path,
            profile_id=profile.profile_id,
            profile_name=profile.display_name,
            value=value,
            unit=profile.unit,
            needle_angle_deg=needle_angle_deg,
            mapping_mode=mapping_mode,
            status=status,
            message=message,
            gauge_confidence=None if gauge_detection is None else gauge_detection.confidence,
            center_confidence=None if points is None or points.center is None else points.center.confidence,
            tip_confidence=None if points is None or points.tip is None else points.tip.confidence,
            min_confidence=None if points is None or points.min_point is None else points.min_point.confidence,
            max_confidence=None if points is None or points.max_point is None else points.max_point.confidence,
            overlay_path=overlay_path,
        )

    def _stage2_points_to_image_points(self, points: Stage2Points, crop_info: CropInfo) -> Stage2Points:
        return Stage2Points(
            center=self._point_to_image(points.center, crop_info),
            tip=self._point_to_image(points.tip, crop_info),
            min_point=self._point_to_image(points.min_point, crop_info),
            max_point=self._point_to_image(points.max_point, crop_info),
        )

    def _point_to_image(self, point: Point2D | None, crop_info: CropInfo) -> Point2D | None:
        if point is None:
            return None

        x, y = self.cropper.point_from_crop_to_image(crop_info, point.x, point.y)
        return Point2D(x=x, y=y, confidence=point.confidence)

    def _overlay_path(self, output_dir: Path, profile_folder_name: str, image_path: Path) -> Path:
        return output_dir / "overlays" / profile_folder_name / f"{image_path.stem}_overlay.jpg"
