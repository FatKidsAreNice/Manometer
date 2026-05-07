from pathlib import Path

from PIL import Image, ImageOps


class ImageLoader:
    def load_rgb(self, image_path: Path) -> Image.Image:
        image = Image.open(image_path.expanduser().resolve())
        image = ImageOps.exif_transpose(image)
        return image.convert("RGB")
