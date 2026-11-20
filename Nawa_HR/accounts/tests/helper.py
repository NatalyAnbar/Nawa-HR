from io import BytesIO
from urllib.parse import parse_qs, urlparse

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def make_photo(name="test", extension="png", width=400, height=400, size_mb=None):
    """Build a valid in-memory image file, optionally padded to an exact size in MB."""
    photo = Image.new("RGB", (width, height), color="red")
    photo_format = "jpeg" if extension == "jpg" else extension

    buffer = BytesIO()
    photo.save(buffer, photo_format.upper())

    if size_mb:
        target_bytes = int(size_mb * 1024 * 1024)
        current_bytes = buffer.tell()
        if target_bytes > current_bytes:
            buffer.write(b"\0" * (target_bytes - current_bytes))

    return SimpleUploadedFile(
        f"{name}.{extension}",
        buffer.getvalue(),
        content_type=f"image/{photo_format}",
    )


def params_from_link(link):
    """Extract uid and token query parameters from an invite or password reset link."""
    query = parse_qs(urlparse(link).query)
    return {"uid": query["uid"][0], "token": query["token"][0]}
