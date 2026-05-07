import math

from app.models import CalibrationPoint


class AngleMath:
    @staticmethod
    def calculate_angle_deg(center_x: float, center_y: float, point_x: float, point_y: float) -> float:
        dx = point_x - center_x
        dy = center_y - point_y

        angle = math.degrees(math.atan2(dy, dx))

        if angle < 0.0:
            angle += 360.0

        return angle

    @staticmethod
    def infer_direction(points: list[CalibrationPoint]) -> str:
        signed_deltas: list[float] = []

        for current, next_point in zip(points, points[1:]):
            delta = ((next_point.angle_deg - current.angle_deg + 180.0) % 360.0) - 180.0

            if abs(delta) > 1e-6:
                signed_deltas.append(delta)

        if not signed_deltas:
            return "clockwise"

        average_delta = sum(signed_deltas) / len(signed_deltas)
        return "counterclockwise" if average_delta > 0.0 else "clockwise"

    @staticmethod
    def unwrap_calibration_angles(points: list[CalibrationPoint], direction: str) -> list[tuple[float, float]]:
        if not points:
            return []

        unwrapped: list[tuple[float, float]] = [(points[0].value, points[0].angle_deg)]
        previous_angle = points[0].angle_deg

        for point in points[1:]:
            angle = point.angle_deg

            if direction == "counterclockwise":
                delta = (angle - previous_angle) % 360.0
                if delta == 0.0:
                    delta = 360.0
                unwrapped_angle = previous_angle + delta
            else:
                delta = (previous_angle - angle) % 360.0
                if delta == 0.0:
                    delta = 360.0
                unwrapped_angle = previous_angle - delta

            unwrapped.append((point.value, unwrapped_angle))
            previous_angle = unwrapped_angle

        return unwrapped

    @staticmethod
    def unwrap_angle_near_range(angle_deg: float, unwrapped_points: list[tuple[float, float]]) -> float:
        angles = [item[1] for item in unwrapped_points]
        min_angle = min(angles)
        max_angle = max(angles)
        center = (min_angle + max_angle) / 2.0
        candidates = [angle_deg + 360.0 * offset for offset in range(-3, 4)]
        return min(candidates, key=lambda candidate: abs(candidate - center))

    @staticmethod
    def unwrap_angle_from_start(angle_deg: float, start_angle: float, direction: str) -> float:
        if direction == "counterclockwise":
            delta = (angle_deg - start_angle) % 360.0
            return start_angle + delta

        delta = (start_angle - angle_deg) % 360.0
        return start_angle - delta

    @staticmethod
    def interpolate_value_from_unwrapped_angle(
        unwrapped_angle: float,
        unwrapped_points: list[tuple[float, float]],
        min_value: float,
        max_value: float,
    ) -> float:
        for current_point, next_point in zip(unwrapped_points, unwrapped_points[1:]):
            current_value, current_angle = current_point
            next_value, next_angle = next_point
            segment_min = min(current_angle, next_angle)
            segment_max = max(current_angle, next_angle)

            if segment_min <= unwrapped_angle <= segment_max:
                if abs(next_angle - current_angle) < 1e-9:
                    return current_value

                t = (unwrapped_angle - current_angle) / (next_angle - current_angle)
                value = current_value + t * (next_value - current_value)
                return min(max(value, min_value), max_value)

        nearest_point = min(unwrapped_points, key=lambda point: abs(point[1] - unwrapped_angle))
        return min(max(nearest_point[0], min_value), max_value)
