import io

import pytest
from PIL import Image

from app.patterns.validators.image_validators import (
    ImageValidationError,
    SizeValidator,
    UploadedImage,
    build_image_validation_chain,
)
from tests.conftest import make_photo


def validate(data: bytes) -> UploadedImage:
    return build_image_validation_chain().validate(UploadedImage(data))


def test_valid_photo_passes_the_whole_chain():
    upload = validate(make_photo())
    assert upload.content_type == "image/jpeg"
    assert upload.image.size == (800, 600)


def test_png_and_webp_are_accepted():
    assert validate(make_photo(fmt="PNG")).content_type == "image/png"
    assert validate(make_photo(fmt="WEBP")).content_type == "image/webp"


def test_format_validator_rejects_non_images():
    with pytest.raises(ImageValidationError, match="JPG, PNG o WEBP"):
        validate(b"%PDF-1.7 not an image")


def test_size_validator_rejects_heavy_files():
    with pytest.raises(ImageValidationError, match="pesa demasiado"):
        SizeValidator(max_mb=0.001).validate(UploadedImage(make_photo()))


def test_resolution_validator_rejects_tiny_photos():
    with pytest.raises(ImageValidationError, match="muy pequeña"):
        validate(make_photo(size=(120, 90)))


def test_content_validator_rejects_blank_or_stretched_images():
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (255, 255, 255)).save(buffer, "JPEG")
    with pytest.raises(ImageValidationError, match="vacía"):
        validate(buffer.getvalue())
    with pytest.raises(ImageValidationError, match="alargada"):
        validate(make_photo(size=(2000, 300)))


def test_corrupted_image_is_rejected():
    data = make_photo()[:200]
    with pytest.raises(ImageValidationError, match="No pudimos abrir"):
        validate(data)
