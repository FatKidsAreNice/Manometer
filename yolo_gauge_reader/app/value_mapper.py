from app.angle_math import AngleMath
from app.models import GaugeProfile, Stage2Points


class GaugeValueMapper:
    def map_value(
        self,
        profile: GaugeProfile,
        needle_angle_deg: float,
        points: Stage2Points,
        mapping_mode: str,
    ) -> tuple[float | None, str, str]:
        if mapping_mode in {"auto", "detected_minmax"}:
            mapped = self._map_with_detected_minmax(profile, needle_angle_deg, points)

            if mapped is not None:
                value, message = mapped
                return value, "detected_minmax", message

            if mapping_mode == "detected_minmax":
                return None, "manual_review", "min/max wurden nicht ausreichend erkannt."

        value = self._map_with_profile(profile, needle_angle_deg)
        return value, "profile", "Wert über Profil-Kalibrierwinkel berechnet."

    def _map_with_profile(self, profile: GaugeProfile, needle_angle_deg: float) -> float:
        direction = AngleMath.infer_direction(profile.calibration_points)
        unwrapped_points = AngleMath.unwrap_calibration_angles(profile.calibration_points, direction)
        needle_unwrapped = AngleMath.unwrap_angle_near_range(needle_angle_deg, unwrapped_points)

        return AngleMath.interpolate_value_from_unwrapped_angle(
            unwrapped_angle=needle_unwrapped,
            unwrapped_points=unwrapped_points,
            min_value=profile.min_value,
            max_value=profile.max_value,
        )

    def _map_with_detected_minmax(
        self,
        profile: GaugeProfile,
        needle_angle_deg: float,
        points: Stage2Points,
    ) -> tuple[float, str] | None:
        if points.center is None or points.min_point is None or points.max_point is None:
            return None

        direction = AngleMath.infer_direction(profile.calibration_points)
        reference_points = AngleMath.unwrap_calibration_angles(profile.calibration_points, direction)

        image_min_angle = AngleMath.calculate_angle_deg(
            points.center.x,
            points.center.y,
            points.min_point.x,
            points.min_point.y,
        )
        image_max_angle = AngleMath.calculate_angle_deg(
            points.center.x,
            points.center.y,
            points.max_point.x,
            points.max_point.y,
        )

        image_min_unwrapped = image_min_angle
        image_max_unwrapped = AngleMath.unwrap_angle_from_start(image_max_angle, image_min_unwrapped, direction)
        needle_unwrapped = AngleMath.unwrap_angle_from_start(needle_angle_deg, image_min_unwrapped, direction)

        denominator = image_max_unwrapped - image_min_unwrapped

        if abs(denominator) < 1e-9:
            return None

        t = (needle_unwrapped - image_min_unwrapped) / denominator

        if t < -0.08 or t > 1.08:
            return None

        t = min(max(t, 0.0), 1.0)

        reference_min_angle = reference_points[0][1]
        reference_max_angle = reference_points[-1][1]
        reference_angle = reference_min_angle + t * (reference_max_angle - reference_min_angle)

        value = AngleMath.interpolate_value_from_unwrapped_angle(
            unwrapped_angle=reference_angle,
            unwrapped_points=reference_points,
            min_value=profile.min_value,
            max_value=profile.max_value,
        )

        return value, "Wert über erkannte min/max-Punkte und Profil-Skala berechnet."
