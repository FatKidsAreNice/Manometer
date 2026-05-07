from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CalibrationPoint:
    value: float
    angle_deg: float


@dataclass(frozen=True)
class GaugeProfile:
    profile_id: str
    display_name: str
    folder_name: str
    unit: str
    min_value: float
    max_value: float
    calibration_points: list[CalibrationPoint]


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass(frozen=True)
class CropInfo:
    x1: int
    y1: int
    x2: int
    y2: int
    width: int
    height: int


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float
    confidence: float


@dataclass(frozen=True)
class Stage2Points:
    center: Point2D | None
    tip: Point2D | None
    min_point: Point2D | None
    max_point: Point2D | None


@dataclass(frozen=True)
class ReadingResult:
    image_path: Path
    profile_id: str
    profile_name: str
    value: float | None
    unit: str
    needle_angle_deg: float | None
    mapping_mode: str
    status: str
    message: str
    gauge_confidence: float | None
    center_confidence: float | None
    tip_confidence: float | None
    min_confidence: float | None
    max_confidence: float | None
    overlay_path: Path | None
