"""FastAPI app: routes, error responses, CORS.

Run from the repo root:  uvicorn backend.main:app --reload
Then open http://127.0.0.1:8000/docs to try the API.
"""
import os

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.engine import mask_text
from backend.files import MAX_FILE_BYTES, APIError, read_upload
from backend.schemas import SUPPORTED_TYPES, ErrorResponse, MaskRequest, MaskResponse

MAX_TEXT_CHARS = MAX_FILE_BYTES  # same budget as a file upload

app = FastAPI(title="MaskData API", version="0.1.0")

# Comma-separated list, e.g. "http://127.0.0.1:5500,https://maskdata.example.com".
# Default "*" is for local development only.
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Empty text, bad `types`, undecodable file, bad image, or no text in image"},
    413: {"model": ErrorResponse, "description": "Text, file or image too large"},
    415: {"model": ErrorResponse, "description": "Unsupported file type"},
    500: {"model": ErrorResponse, "description": "Tesseract failed to read the image"},
    503: {"model": ErrorResponse, "description": "Tesseract or its Thai data is not installed"},
    504: {"model": ErrorResponse, "description": "OCR took too long"},
}


def error_json(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"ok": False, "error": {"code": code, "message": message}})


@app.exception_handler(APIError)
async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    return error_json(exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
    message = f"{where}: {first.get('msg', 'invalid request')}" if where else first.get("msg", "Invalid request.")
    return error_json(400, "INVALID_REQUEST", message)


def normalize_types(types: list[str] | None) -> list[str] | None:
    """Accept a list or comma-separated values; reject unknown names."""
    if types is None:
        return None
    names = [t.strip() for item in types for t in item.split(",") if t.strip()]
    unknown = [t for t in names if t not in SUPPORTED_TYPES]
    if unknown:
        raise APIError(400, "INVALID_TYPES",
                       f"Unknown types: {', '.join(unknown)}. Allowed: {', '.join(SUPPORTED_TYPES)}.")
    return names


def run_mask(text: str, types: list[str] | None, source: dict) -> dict:
    if not text.strip():
        raise APIError(400, "EMPTY_TEXT", "Text is empty.")
    result = mask_text(text, normalize_types(types))
    return {"ok": True, "source": source, **{k: v for k, v in result.items() if k != "ok"}}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/mask", response_model=MaskResponse, responses=ERROR_RESPONSES)
def mask(body: MaskRequest) -> dict:
    if len(body.text) > MAX_TEXT_CHARS:
        raise APIError(413, "TEXT_TOO_LARGE", f"Text is longer than {MAX_TEXT_CHARS} characters.")
    return run_mask(body.text, body.types, {"kind": "text"})


@app.post("/api/mask/file", response_model=MaskResponse, responses=ERROR_RESPONSES)
async def mask_file(file: UploadFile = File(...), types: list[str] | None = Form(None)) -> dict:
    data = await file.read(MAX_FILE_BYTES + 1)  # one extra byte is enough to detect "too large"
    # OCR can take seconds, so run it off the event loop to keep other requests responsive
    text, file_type = await run_in_threadpool(read_upload, file.filename, data)
    source = {"kind": "file", "filename": file.filename, "file_type": file_type, "ocr": file_type == "png"}
    return run_mask(text, types, source)
