from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
MAX_IMAGE_FILE_SIZE_MB = 5
MAX_ASPECT_RATIO = 2

validate_photo_extension = FileExtensionValidator(
    allowed_extensions=ALLOWED_IMAGE_EXTENSIONS
)


def validate_photo_file_size(photo):
    """Reject files larger than MAX_IMAGE_FILE_SIZE_MB."""

    if photo.size > MAX_IMAGE_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"Photo file must be {MAX_IMAGE_FILE_SIZE_MB} MB or smaller."
        )


def validate_photo_aspect_ratio(photo):
    """Reject photos that are too wide or too tall (beyond MAX_ASPECT_RATIO:1)."""

    width, height = get_image_dimensions(photo)
    ratio = max(width, height) / min(width, height)

    if ratio > MAX_ASPECT_RATIO:
        raise ValidationError(
            f"Photo proportions must not exceed {MAX_ASPECT_RATIO}:1."
        )


PHOTO_VALIDATORS = [
    validate_photo_extension,
    validate_photo_file_size,
    validate_photo_aspect_ratio,
]
