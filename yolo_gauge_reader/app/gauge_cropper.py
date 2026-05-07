from PIL import Image

from app.models import CropInfo, Detection


class GaugeCropper:
    def crop(self, image: Image.Image, gauge_detection: Detection, padding: float) -> tuple[Image.Image, CropInfo]:
        image_width, image_height = image.size
        side_length = max(gauge_detection.width, gauge_detection.height) * padding

        crop_x1 = gauge_detection.center_x - side_length / 2.0
        crop_y1 = gauge_detection.center_y - side_length / 2.0
        crop_x2 = gauge_detection.center_x + side_length / 2.0
        crop_y2 = gauge_detection.center_y + side_length / 2.0

        if crop_x1 < 0.0:
            crop_x2 -= crop_x1
            crop_x1 = 0.0

        if crop_y1 < 0.0:
            crop_y2 -= crop_y1
            crop_y1 = 0.0

        if crop_x2 > image_width:
            overflow = crop_x2 - image_width
            crop_x1 -= overflow
            crop_x2 = float(image_width)

        if crop_y2 > image_height:
            overflow = crop_y2 - image_height
            crop_y1 -= overflow
            crop_y2 = float(image_height)

        crop_x1 = max(0.0, crop_x1)
        crop_y1 = max(0.0, crop_y1)
        crop_x2 = min(float(image_width), crop_x2)
        crop_y2 = min(float(image_height), crop_y2)

        crop_info = CropInfo(
            x1=int(round(crop_x1)),
            y1=int(round(crop_y1)),
            x2=int(round(crop_x2)),
            y2=int(round(crop_y2)),
            width=int(round(crop_x2 - crop_x1)),
            height=int(round(crop_y2 - crop_y1)),
        )

        cropped_image = image.crop((crop_info.x1, crop_info.y1, crop_info.x2, crop_info.y2))
        return cropped_image, crop_info

    def point_from_crop_to_image(self, crop_info: CropInfo, x: float, y: float) -> tuple[float, float]:
        return crop_info.x1 + x, crop_info.y1 + y
