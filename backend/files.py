"""Upload validation and text decoding for POST /api/mask/file."""
import os

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = {".txt", ".csv"}  # .png comes later with OCR
ENCODINGS = ("utf-8-sig", "cp874")  # cp874 = Thai Windows files


class APIError(Exception):
    """An error that becomes {"ok": false, "error": {...}} with the given HTTP status."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def file_type_of(filename: str | None) -> str:
    """Return the extension without the dot, or raise 415 if it is not supported."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise APIError(415, "UNSUPPORTED_FILE_TYPE", f"Only {allowed} files are supported.")
    return ext[1:]


def check_size(data: bytes) -> None:
    if len(data) > MAX_FILE_BYTES:
        raise APIError(413, "FILE_TOO_LARGE", f"File is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")


def decode_text(data: bytes) -> str:
    """Decode bytes as UTF-8 (BOM allowed), then cp874; normalise line endings to \\n."""
    for encoding in ENCODINGS:
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise APIError(400, "DECODE_FAILED", "File is not readable text (expected UTF-8 or Thai Windows encoding).")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_upload(filename: str | None, data: bytes) -> tuple[str, str]:
    """Validate an uploaded file and return (text, file_type)."""
    file_type = file_type_of(filename)
    check_size(data)
    return decode_text(data), file_type
