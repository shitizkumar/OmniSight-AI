from pathlib import Path
from PIL import Image


def crop_region(
    image_path: str | Path,
    box: dict[str, int],
    output_path: str | Path,
    padding: int = 20,
) -> dict:
    """Crop a defect region with surrounding visual context."""

    image_path = Path(image_path)
    output_path = Path(output_path)

    if not image_path.is_file():
        raise FileNotFoundError(f"Screenshot not found: {image_path}")

    if padding < 0:
        raise ValueError("Padding cannot be negative.")

    if not all(
        isinstance(box.get(key), int) and not isinstance(box.get(key), bool)
        for key in ("x", "y", "width", "height")
    ):
        raise ValueError("Box must contain integer x, y, width and height.")

    x, y = box["x"], box["y"]
    width, height = box["width"], box["height"]

    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("Invalid crop coordinates or dimensions.")

    with Image.open(image_path) as image:
        image_width, image_height = image.size

        left = max(0, x - padding)
        top = max(0, y - padding)
        right = min(image_width, x + width + padding)
        bottom = min(image_height, y + height + padding)

        if left >= right or top >= bottom:
            raise ValueError("Defect region does not overlap the screenshot.")

        crop = image.crop((left, top, right, bottom))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(output_path)

    return {
        "status": "success",
        "output_path": str(output_path),
        "source_size": (image_width, image_height),
        "crop_size": crop.size,
        "crop_box": (left, top, right, bottom),
    }