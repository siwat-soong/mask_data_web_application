"""PNG to text with Tesseract OCR, for POST /api/mask/file.

pytesseract only calls the Tesseract program, so the program and its Thai data
must be installed on the machine as well:
  Windows:        https://github.com/UB-Mannheim/tesseract/wiki  (tick Thai under "Additional language data")
  Debian/Ubuntu:  apt install tesseract-ocr tesseract-ocr-tha
Set TESSERACT_CMD to the full path of tesseract if it is not on PATH.
"""
import io
import os
import re
import shutil

import pytesseract
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from backend.files import APIError

LANGUAGES = "tha+eng"
MAX_PIXELS = 25_000_000  # about 5000 x 5000
UPSCALE_BELOW = 2000  # images smaller than this on both sides are enlarged 2x; Tesseract reads larger text better
TIMEOUT_SECONDS = 30
WINDOWS_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # the installer does not add itself to PATH

DASHES = re.compile(r"[\u2010-\u2015\u2212]")  # hyphen, en dash, em dash, minus sign...
SPACED_DASH = re.compile(r"(?<=\d)[ \t]*-[ \t]*(?=\d)")  # "093 - 245" -> "093-245"
SPACE_BEFORE_COLON = re.compile(r"[ \t]+:")  # "DOB :" -> "DOB:"


def find_tesseract() -> str | None:
    cmd = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    if cmd:
        return cmd
    return WINDOWS_DEFAULT if os.path.exists(WINDOWS_DEFAULT) else None


def load_image(data: bytes) -> Image.Image:
    """Open PNG bytes, or raise 400 if they are not a PNG and 413 if the image is huge."""
    try:
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise APIError(400, "INVALID_IMAGE", "File is not a readable PNG image.")
    if image.format != "PNG":
        raise APIError(400, "INVALID_IMAGE", "File is not a readable PNG image.")
    if image.width * image.height > MAX_PIXELS:
        raise APIError(413, "IMAGE_TOO_LARGE", f"Image is larger than {MAX_PIXELS:,} pixels.")
    try:
        image.load()
    except OSError:
        raise APIError(400, "INVALID_IMAGE", "PNG image is damaged or incomplete.")
    return image


def prepare(image: Image.Image) -> Image.Image:
    """Greyscale, dark text on a light background, enlarged if small."""
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        # transparent pixels would turn black and hide dark text
        background = Image.new("RGBA", image.size, "white")
        image = Image.alpha_composite(background, image.convert("RGBA"))
    image = ImageOps.grayscale(image)
    if ImageStat.Stat(image).mean[0] < 128:  # dark-mode screenshot
        image = ImageOps.invert(image)
    if max(image.size) < UPSCALE_BELOW:
        image = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
    return image


def clean_ocr_text(text: str) -> str:
    """Undo common OCR noise that would stop the rules from matching."""
    text = text.replace("\r\n", "\n").replace("\f", "")
    text = DASHES.sub("-", text)
    text = SPACED_DASH.sub("-", text)
    text = SPACE_BEFORE_COLON.sub(":", text)
    return text.strip()


def image_to_text(data: bytes) -> str:
    cmd = find_tesseract()
    if cmd is None:
        raise APIError(503, "OCR_UNAVAILABLE", "Reading images is not available: Tesseract is not installed on the server.")
    pytesseract.pytesseract.tesseract_cmd = cmd

    image = prepare(load_image(data))
    try:
        text = pytesseract.image_to_string(image, lang=LANGUAGES, timeout=TIMEOUT_SECONDS)
    except pytesseract.TesseractNotFoundError:
        raise APIError(503, "OCR_UNAVAILABLE", "Reading images is not available: Tesseract could not be started.")
    except pytesseract.TesseractError as exc:
        if "Failed loading language" in str(exc):
            raise APIError(503, "OCR_UNAVAILABLE", "Reading images is not available: Thai language data for Tesseract is missing.")
        raise APIError(500, "OCR_FAILED", "Tesseract could not read this image.")
    except RuntimeError:  # pytesseract's timeout
        raise APIError(504, "OCR_TIMEOUT", f"Reading the image took longer than {TIMEOUT_SECONDS} seconds.")

    text = clean_ocr_text(text)
    if not text:
        raise APIError(400, "NO_TEXT_FOUND", "No text was found in the image.")
    return text
