import json
from pathlib import Path
from typing import Any

from app.models import CalibrationPoint, GaugeProfile


class ProfileRepository:
    def load(self, profile_path: Path) -> GaugeProfile:
        profile_path = profile_path.expanduser().resolve()

        if not profile_path.exists():
            raise FileNotFoundError(f"Profil nicht gefunden: {profile_path}")

        with profile_path.open("r", encoding="utf-8") as file:
            raw_profile = json.load(file)

        return self._parse(raw_profile, profile_path)

    def _parse(self, raw_profile: dict[str, Any], profile_path: Path) -> GaugeProfile:
        measurement = raw_profile.get("measurement", {})
        calibration = raw_profile.get("calibration", {})
        points: list[CalibrationPoint] = []

        for raw_point in calibration.get("points", []):
            value = raw_point.get("value")
            angle_deg = raw_point.get("angle_deg")

            if value is None:
                raise ValueError(f"Kalibrierpunkt ohne value in {profile_path}")

            if angle_deg is None:
                raise ValueError(f"Kalibrierpunkt {value} ohne angle_deg in {profile_path}")

            points.append(CalibrationPoint(value=float(value), angle_deg=float(angle_deg) % 360.0))

        if len(points) < 2:
            raise ValueError(f"Mindestens zwei Kalibrierpunkte erforderlich: {profile_path}")

        points = sorted(points, key=lambda point: point.value)

        return GaugeProfile(
            profile_id=str(raw_profile.get("profile_id", profile_path.parent.name)),
            display_name=str(raw_profile.get("display_name", profile_path.parent.name)),
            folder_name=str(raw_profile.get("folder_name", profile_path.parent.name)),
            unit=str(measurement.get("unit", "")),
            min_value=float(measurement.get("min_value", points[0].value)),
            max_value=float(measurement.get("max_value", points[-1].value)),
            calibration_points=points,
        )
