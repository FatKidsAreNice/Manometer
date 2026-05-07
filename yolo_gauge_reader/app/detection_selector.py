from app.angle_math import AngleMath
from app.models import Detection, Point2D, Stage2Points


class DetectionSelector:
    FULL_IMAGE_GAUGE_CLASS_ID = 1

    CROP_CENTER_CLASS_ID = 0
    CROP_MAX_CLASS_ID = 1
    CROP_MIN_CLASS_ID = 2
    CROP_TIP_CLASS_ID = 3

    def select_gauge(self, detections: list[Detection]) -> Detection | None:
        gauges = [detection for detection in detections if detection.class_id == self.FULL_IMAGE_GAUGE_CLASS_ID]

        if not gauges:
            return None

        return max(gauges, key=lambda detection: detection.confidence)

    def select_stage2_points(self, detections: list[Detection]) -> Stage2Points:
        center_detection = self._highest_confidence(detections, self.CROP_CENTER_CLASS_ID)
        min_detection = self._highest_confidence(detections, self.CROP_MIN_CLASS_ID)
        max_detection = self._highest_confidence(detections, self.CROP_MAX_CLASS_ID)

        center = self._to_point(center_detection)
        min_point = self._to_point(min_detection)
        max_point = self._to_point(max_detection)

        tip_detection = self._select_tip(detections, center, min_point, max_point)

        return Stage2Points(
            center=center,
            tip=self._to_point(tip_detection),
            min_point=min_point,
            max_point=max_point,
        )

    def _highest_confidence(self, detections: list[Detection], class_id: int) -> Detection | None:
        candidates = [detection for detection in detections if detection.class_id == class_id]

        if not candidates:
            return None

        return max(candidates, key=lambda detection: detection.confidence)

    def _select_tip(
        self,
        detections: list[Detection],
        center: Point2D | None,
        min_point: Point2D | None,
        max_point: Point2D | None,
    ) -> Detection | None:
        candidates = [detection for detection in detections if detection.class_id == self.CROP_TIP_CLASS_ID]

        if not candidates:
            return None

        if center is None:
            return max(candidates, key=lambda detection: detection.confidence)

        scored_candidates = []

        for candidate in candidates:
            angle_score = self._angle_range_score(center, min_point, max_point, candidate)
            score = candidate.confidence + 0.25 * angle_score
            scored_candidates.append((score, candidate))

        return max(scored_candidates, key=lambda item: item[0])[1]

    def _angle_range_score(
        self,
        center: Point2D,
        min_point: Point2D | None,
        max_point: Point2D | None,
        tip_detection: Detection,
    ) -> float:
        if min_point is None or max_point is None:
            return 0.0

        min_angle = AngleMath.calculate_angle_deg(center.x, center.y, min_point.x, min_point.y)
        max_angle = AngleMath.calculate_angle_deg(center.x, center.y, max_point.x, max_point.y)
        tip_angle = AngleMath.calculate_angle_deg(center.x, center.y, tip_detection.center_x, tip_detection.center_y)

        clockwise_delta = (min_angle - max_angle) % 360.0
        clockwise_tip_delta = (min_angle - tip_angle) % 360.0

        counter_delta = (max_angle - min_angle) % 360.0
        counter_tip_delta = (tip_angle - min_angle) % 360.0

        tolerance = 12.0

        clockwise_ok = clockwise_tip_delta <= clockwise_delta + tolerance
        counter_ok = counter_tip_delta <= counter_delta + tolerance

        return 1.0 if clockwise_ok or counter_ok else 0.0

    def _to_point(self, detection: Detection | None) -> Point2D | None:
        if detection is None:
            return None

        return Point2D(x=detection.center_x, y=detection.center_y, confidence=detection.confidence)
