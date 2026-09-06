"""Image handling: validate, resize/compress, save to disk, and encode as data URI."""

import base64
import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException, UploadFile, status

MAX_IMAGE_SIZE = (1024, 1024)
UPLOAD_EXT = ".jpg"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


def _normalise(upload: UploadFile) -> Image.Image:
    """Open the uploaded file, convert to RGB, downscale, and re-encode as JPEG."""
    try:
        raw = upload.file.read()
        img = Image.open(io.BytesIO(raw))
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a supported image type.",
        )
    img = img.convert("RGB")
    img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
    return img


def save_upload(upload: UploadFile, upload_dir: str) -> tuple[str, str]:
    """
    Persist an uploaded waste photo to disk.

    Returns (public_url, abs_path). public_url is used by the frontend to show the
    image; abs_path is used by the classification pipeline.
    """
    if upload.content_type and upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {upload.content_type}",
        )

    img = _normalise(upload)
    folder = Path(upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{UPLOAD_EXT}"
    abs_path = folder / filename
    img.save(abs_path, "JPEG", quality=88)

    return f"/uploads/{filename}", str(abs_path.resolve())


def to_base64(abs_path: str) -> str:
    """Return the raw base64 payload of an image file."""
    with open(abs_path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def to_data_uri(abs_path: str, mime: str = "image/jpeg") -> str:
    """Return the image encoded as a data URI suitable for NIM image_url.url."""
    return f"data:{mime};base64,{to_base64(abs_path)}"