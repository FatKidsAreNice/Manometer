from pathlib import Path

from PIL import Image
from ultralytics import YOLO

from app.models import Detection


class YoloPredictor:
    def __init__(self, model_path: Path, class_names: dict[int, str], image_size: int, confidence: float):
        self.model_path = model_path.expanduser().resolve()
        self.class_names = class_names
        self.image_size = image_size
        self.confidence = confidence
        self.model = YOLO(str(self.model_path))

    def predict(self, image: Image.Image) -> list[Detection]:
        results = self.model.predict(
            source=image,
            imgsz=self.image_size,
            conf=self.confidence,
            verbose=False,
        )

        if not results:
            return []

        result = results[0]

        if result.boxes is None:
            return []

        detections: list[Detection] = []

        for box in result.boxes:
            class_id = int(box.cls.item())
            xyxy = box.xyxy[0].tolist()

            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=self.class_names.get(class_id, str(class_id)),
                    confidence=float(box.conf.item()),
                    x1=float(xyxy[0]),
                    y1=float(xyxy[1]),
                    x2=float(xyxy[2]),
                    y2=float(xyxy[3]),
                )
            )

        return detections
