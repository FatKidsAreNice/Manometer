from pathlib import Path


class ImageScanner:
    SUPPORTED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    }

    def find_profile_folders(self, input_dir: Path) -> list[Path]:
        input_dir = input_dir.expanduser().resolve()

        if not input_dir.exists():
            raise FileNotFoundError(f"Eingabeordner existiert nicht: {input_dir}")

        folders = [
            folder
            for folder in input_dir.iterdir()
            if folder.is_dir() and (folder / "gauge_profile.json").exists()
        ]

        return sorted(folders, key=lambda item: item.name.lower())

    def find_images(self, folder: Path, max_images: int = 0) -> list[Path]:
        images = [
            image_path.resolve()
            for image_path in folder.iterdir()
            if image_path.is_file() and image_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

        images = sorted(images, key=lambda item: item.name.lower())

        if max_images > 0:
            return images[:max_images]

        return images
