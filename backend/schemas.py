"""JSON request/response models. These drive the examples shown at /docs."""
from typing import Literal

from pydantic import BaseModel

SUPPORTED_TYPES = ("credit_card", "email", "phone", "dob", "address")


class MaskRequest(BaseModel):
    text: str
    types: list[str] | None = None  # None = all five types


class Span(BaseModel):
    start: int  # [start, end) Python string index
    end: int
    text: str


class Detection(BaseModel):
    id: int
    type: str
    original: Span
    masked: Span
    chars_masked: int


class ErrorItem(BaseModel):
    type: str
    code: str
    message: str
    original: Span


class TypeSummary(BaseModel):
    count: int
    chars_masked: int
    errors: int


class Summary(BaseModel):
    total_detections: int
    total_chars_masked: int
    total_errors: int
    by_type: dict[str, TypeSummary]


class Source(BaseModel):
    kind: Literal["text", "file"]
    filename: str | None = None
    file_type: str | None = None
    ocr: bool = False


class MaskResponse(BaseModel):
    ok: Literal[True] = True
    source: Source
    original_text: str
    masked_text: str
    detections: list[Detection]
    errors: list[ErrorItem]
    summary: Summary


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorDetail
