import pytest
from PIL import Image

from vision_engine.image_cropper import crop_region


@pytest.fixture
def screenshot(tmp_path):
    image_path = tmp_path / "screenshot.png"
    Image.new("RGB", (800, 600), "white").save(image_path)
    return image_path


def test_crop_region_with_padding(screenshot, tmp_path):
    output = tmp_path / "crops" / "defect.png"

    result = crop_region(
        screenshot,
        {"x": 100, "y": 120, "width": 200, "height": 100},
        output,
        padding=20,
    )

    assert result["status"] == "success"
    assert result["crop_box"] == (80, 100, 320, 240)
    assert result["crop_size"] == (240, 140)
    assert output.is_file()


def test_crop_clamps_to_image_boundaries(screenshot, tmp_path):
    output = tmp_path / "edge.png"

    result = crop_region(
        screenshot,
        {"x": 0, "y": 0, "width": 50, "height": 50},
        output,
        padding=20,
    )

    assert result["crop_box"] == (0, 0, 70, 70)


@pytest.mark.parametrize(
    "box",
    [
        {"x": -1, "y": 0, "width": 20, "height": 20},
        {"x": 0, "y": 0, "width": 0, "height": 20},
        {"x": 0, "y": 0, "width": 20, "height": -1},
        {"x": 0, "y": 0, "width": 20},
    ],
)
def test_invalid_coordinates(screenshot, tmp_path, box):
    with pytest.raises(ValueError):
        crop_region(screenshot, box, tmp_path / "invalid.png")


def test_region_outside_image(screenshot, tmp_path):
    with pytest.raises(ValueError, match="does not overlap"):
        crop_region(
            screenshot,
            {"x": 900, "y": 700, "width": 50, "height": 50},
            tmp_path / "outside.png",
        )


def test_missing_screenshot(tmp_path):
    with pytest.raises(FileNotFoundError):
        crop_region(
            tmp_path / "missing.png",
            {"x": 10, "y": 10, "width": 20, "height": 20},
            tmp_path / "output.png",
        )


def test_negative_padding(screenshot, tmp_path):
    with pytest.raises(ValueError, match="Padding"):
        crop_region(
            screenshot,
            {"x": 10, "y": 10, "width": 20, "height": 20},
            tmp_path / "output.png",
            padding=-1,
        )