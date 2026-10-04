# Run from the repo root:  python -m pytest backend/tests/test_ocr.py -v
# Tests marked "real_tesseract" are skipped when Tesseract is not installed.
import io
import os
from unittest.mock import patch

import pytest
import pytesseract
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from backend import main, ocr

client = TestClient(main.app)

# Fonts with Thai glyphs, used only to draw the real Thai test image
THAI_FONTS = [
    r"C:\Windows\Fonts\tahoma.ttf",
    "/usr/share/fonts/truetype/tlwg/Garuda.ttf",  # Debian package fonts-tlwg-garuda-ttf (Docker test image)
]
THAI_FONT = next((path for path in THAI_FONTS if os.path.exists(path)), None)


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def text_png(lines: list[str], font=None, size=(1400, 300)) -> bytes:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    font = font or ImageFont.load_default(size=36)
    for i, line in enumerate(lines):
        draw.text((30, 30 + i * 60), line, fill="black", font=font)
    return png_bytes(image)


def upload_png(data: bytes, name: str = "shot.png"):
    return client.post("/api/mask/file", files={"file": (name, data, "image/png")})


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


@pytest.fixture
def fake_tesseract():
    """Pretend Tesseract is installed; each test sets what it "reads"."""
    with patch.object(ocr, "find_tesseract", return_value="tesseract"), \
         patch.object(ocr.pytesseract, "image_to_string") as read:
        yield read


# ---- API behaviour, with Tesseract faked ----

def test_png_goes_through_ocr_and_engine(fake_tesseract):
    fake_tesseract.return_value = "tel 093 - 245 - 7894\nDOB : 25/12/2549\f"
    r = upload_png(text_png(["anything"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == {"kind": "file", "filename": "shot.png", "file_type": "png", "ocr": True}
    assert body["original_text"] == "tel 093-245-7894\nDOB: 25/12/2549"
    assert body["masked_text"] == "tel XXX-XXX-7894\nDOB: XX/XX/25XX"
    assert fake_tesseract.call_args.kwargs["lang"] == "tha+eng"


def test_txt_still_reports_ocr_false():
    r = client.post("/api/mask/file", files={"file": ("a.txt", b"tel 093-245-7894")})
    assert r.json()["source"]["ocr"] is False


@pytest.mark.parametrize("data", [b"not an image", b"\x89PNG\r\n\x1a\n broken"])
def test_not_a_png(fake_tesseract, data):
    assert_error(upload_png(data), 400, "INVALID_IMAGE")
    fake_tesseract.assert_not_called()


def test_other_image_format_renamed_to_png(fake_tesseract):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="JPEG")
    assert_error(upload_png(buffer.getvalue()), 400, "INVALID_IMAGE")


def test_image_with_too_many_pixels(fake_tesseract):
    huge = png_bytes(Image.new("1", (6000, 5000), 1))  # 30 MP but a tiny file
    assert_error(upload_png(huge), 413, "IMAGE_TOO_LARGE")
    fake_tesseract.assert_not_called()


def test_no_text_in_image(fake_tesseract):
    fake_tesseract.return_value = " \n\f"
    assert_error(upload_png(text_png([])), 400, "NO_TEXT_FOUND")


def test_tesseract_not_installed():
    with patch.object(ocr, "find_tesseract", return_value=None):
        assert_error(upload_png(text_png(["x"])), 503, "OCR_UNAVAILABLE")


@pytest.mark.parametrize("error, status, code", [
    (pytesseract.TesseractNotFoundError(), 503, "OCR_UNAVAILABLE"),
    (pytesseract.TesseractError(1, "Failed loading language 'tha'"), 503, "OCR_UNAVAILABLE"),
    (pytesseract.TesseractError(1, "something else"), 500, "OCR_FAILED"),
    (RuntimeError("Tesseract process timeout"), 504, "OCR_TIMEOUT"),
])
def test_tesseract_failures(fake_tesseract, error, status, code):
    fake_tesseract.side_effect = error
    assert_error(upload_png(text_png(["x"])), status, code)


# ---- image preparation and text clean-up ----

def test_transparent_background_becomes_white():
    image = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((10, 10, 20, 20), fill=(0, 0, 0, 255))
    prepared = ocr.prepare(image)
    assert prepared.mode == "L"
    assert prepared.getpixel((0, 0)) == 255   # was transparent
    assert prepared.getpixel((30, 30)) == 0   # black square, now at 2x scale


def test_dark_mode_is_inverted():
    prepared = ocr.prepare(Image.new("RGB", (50, 50), "black"))
    assert prepared.getpixel((0, 0)) == 255


def test_small_images_are_enlarged_large_ones_are_not():
    assert ocr.prepare(Image.new("RGB", (800, 600), "white")).size == (1600, 1200)
    assert ocr.prepare(Image.new("RGB", (2400, 600), "white")).size == (2400, 600)


@pytest.mark.parametrize("raw, cleaned", [
    ("093 - 245 - 7894", "093-245-7894"),
    ("1234–5678—9012−3456", "1234-5678-9012-3456"),
    ("DOB : 25/12/2549", "DOB: 25/12/2549"),
    ("Address :  689", "Address:  689"),
    ("line1\r\nline2\f", "line1\nline2"),
    ("pre - fix stays", "pre - fix stays"),   # only dashes between digits are joined
    ("1234-5678-90 12-3456", "1234-5678-9012-3456"),
    ("09 3-245-78 94", "093-245-7894"),
    ("DOB:25/12/25 49", "DOB:25/12/2549"),
    ("1234 5678 9012 3456", "1234 5678 9012 3456"),   # no dashes: not a card shape, left for the near-miss
    ("id 12 093-245-7894", "id 12 093-245-7894"),     # a separate number before a phone stays separate
    ("12 34-56", "12 34-56"),                         # joining would not give a full shape
])
def test_clean_ocr_text(raw, cleaned):
    assert ocr.clean_ocr_text(raw) == cleaned


# ---- real Tesseract ----

def tesseract_languages() -> set[str]:
    cmd = ocr.find_tesseract()
    if cmd is None:
        return set()
    pytesseract.pytesseract.tesseract_cmd = cmd
    try:
        return set(pytesseract.get_languages())
    except Exception:
        return set()


LANGS = tesseract_languages()
needs_tesseract = pytest.mark.skipif(not {"eng", "tha"} <= LANGS, reason="Tesseract with eng+tha is not installed")


@needs_tesseract
def test_real_ocr_english_screenshot():
    data = text_png([
        "Customer email: somchai.d@company.com",
        "Phone: 093-245-7894  Card: 1234-5678-9012-3456",
        "DOB:25/12/2549",
    ])
    body = upload_png(data).json()
    assert body["ok"] is True, body
    assert body["source"]["ocr"] is True
    assert "s*******d@company.com" in body["masked_text"]
    assert "XXX-XXX-7894" in body["masked_text"]
    assert "XXXX-XXXX-XXXX-3456" in body["masked_text"]
    assert "DOB:XX/XX/25XX" in body["masked_text"]


@needs_tesseract
@pytest.mark.skipif(THAI_FONT is None, reason="no Thai font to draw the test image")
def test_real_ocr_thai_address():
    data = text_png(["Address: 689 ถนนลาดกระบัง กรุงเทพฯ"], font=ImageFont.truetype(THAI_FONT, 40))
    body = upload_png(data).json()
    assert body["ok"] is True, body
    assert "Address: XXX" in body["masked_text"]
