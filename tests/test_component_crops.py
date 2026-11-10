from PIL import Image

from repair_engine.browser_verifier import crop_component_regions


def test_crop_component_regions_creates_component_images(tmp_path):
    screenshot = tmp_path / "mobile.png"
    Image.new("RGB", (800, 600), "white").save(screenshot)

    boxes = {
        "product": {"x": 50, "y": 60, "width": 200, "height": 100},
        "submit_button": {"x": 300, "y": 400, "width": 120, "height": 40},
    }

    output_dir = tmp_path / "component_crops"

    result = crop_component_regions(screenshot, boxes, output_dir)

    assert set(result) == {"product", "submit_button"}

    for name in boxes:
        crop_path = output_dir / f"{name}.png"
        assert crop_path.is_file()
        assert result[name]["path"] == str(crop_path.resolve())
        assert result[name]["crop_size"][0] > 0
        assert result[name]["crop_size"][1] > 0


def test_crop_component_regions_handles_empty_boxes(tmp_path):
    result = crop_component_regions(
        tmp_path / "mobile.png",
        {},
        tmp_path / "component_crops",
    )

    assert result == {}
