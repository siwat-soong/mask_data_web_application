# Run from the repo root:  python -m pytest backend/tests/test_api.py -v
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.files import MAX_FILE_BYTES, decode_text

client = TestClient(main.app)

FAKE_RESULT = {
    "ok": True,
    "original_text": "x",
    "masked_text": "x",
    "detections": [],
    "errors": [],
    "summary": {
        "total_detections": 0,
        "total_chars_masked": 0,
        "total_errors": 0,
        "by_type": {t: {"count": 0, "chars_masked": 0, "errors": 0}
                    for t in ("credit_card", "email", "phone", "dob", "address")},
    },
}


@pytest.fixture
def engine():
    """Replace the engine so these tests only check the API layer."""
    with patch.object(main, "mask_text", return_value=FAKE_RESULT) as fake:
        yield fake


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == code
    assert body["error"]["message"]


# ---- POST /api/mask ----

def test_text_ok(engine):
    r = client.post("/api/mask", json={"text": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["source"] == {"kind": "text", "filename": None, "file_type": None, "ocr": False}
    assert body["summary"] == FAKE_RESULT["summary"]
    engine.assert_called_once_with("hello", None)


def test_text_passes_types(engine):
    client.post("/api/mask", json={"text": "hello", "types": ["email", "phone"]})
    engine.assert_called_once_with("hello", ["email", "phone"])


def test_text_empty_types_list_is_allowed(engine):
    r = client.post("/api/mask", json={"text": "hello", "types": []})
    assert r.status_code == 200
    engine.assert_called_once_with("hello", [])


@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_text_empty(engine, text):
    assert_error(client.post("/api/mask", json={"text": text}), 400, "EMPTY_TEXT")
    engine.assert_not_called()


def test_text_unknown_type(engine):
    r = client.post("/api/mask", json={"text": "hello", "types": ["email", "passport"]})
    assert_error(r, 400, "INVALID_TYPES")
    assert "passport" in r.json()["error"]["message"]


def test_text_missing_field(engine):
    assert_error(client.post("/api/mask", json={"types": ["email"]}), 400, "INVALID_REQUEST")


def test_text_not_json(engine):
    r = client.post("/api/mask", content=b"not json", headers={"Content-Type": "application/json"})
    assert_error(r, 400, "INVALID_REQUEST")


def test_text_too_large(engine):
    r = client.post("/api/mask", json={"text": "a" * (main.MAX_TEXT_CHARS + 1)})
    assert_error(r, 413, "TEXT_TOO_LARGE")


# ---- POST /api/mask/file ----

def upload(name, data, types=None):
    form = {"types": types} if types is not None else None
    return client.post("/api/mask/file", files={"file": (name, data)}, data=form)


@pytest.mark.parametrize("name,file_type", [("log.txt", "txt"), ("bank_log.CSV", "csv")])
def test_file_ok(engine, name, file_type):
    r = upload(name, "card 1234".encode())
    assert r.status_code == 200
    assert r.json()["source"] == {"kind": "file", "filename": name, "file_type": file_type, "ocr": False}
    engine.assert_called_once_with("card 1234", None)


def test_file_types_repeated_and_comma_separated(engine):
    upload("a.txt", b"hi", types=["email", "phone,dob"])
    engine.assert_called_once_with("hi", ["email", "phone", "dob"])


def test_file_unknown_type(engine):
    assert_error(upload("a.txt", b"hi", types=["nope"]), 400, "INVALID_TYPES")


@pytest.mark.parametrize("name", ["photo.jpg", "doc.pdf", "noextension"])
def test_file_wrong_extension(engine, name):
    assert_error(upload(name, b"hi"), 415, "UNSUPPORTED_FILE_TYPE")


def test_file_too_large(engine):
    assert_error(upload("big.txt", b"a" * (MAX_FILE_BYTES + 1)), 413, "FILE_TOO_LARGE")


def test_file_at_size_limit_ok(engine):
    assert upload("max.txt", b"a" * MAX_FILE_BYTES).status_code == 200


def test_file_empty(engine):
    assert_error(upload("empty.txt", b""), 400, "EMPTY_TEXT")


def test_file_missing(engine):
    assert_error(client.post("/api/mask/file"), 400, "INVALID_REQUEST")


def test_file_utf8_bom_and_crlf(engine):
    upload("thai.csv", "﻿ชื่อ,โทร\r\nสมชาย,093-245-7894\r\n".encode("utf-8"))
    engine.assert_called_once_with("ชื่อ,โทร\nสมชาย,093-245-7894\n", None)


def test_file_cp874_thai(engine):
    upload("thai.txt", "ที่อยู่: 689 ถนนลาดกระบัง".encode("cp874"))
    engine.assert_called_once_with("ที่อยู่: 689 ถนนลาดกระบัง", None)


def test_file_undecodable(engine):
    # 0xDB-0xDE and 0xFC-0xFF are undefined in cp874, and this is not UTF-8 either
    assert_error(upload("bin.txt", b"\xff\xfe\xdb\xdc"), 400, "DECODE_FAILED")


# ---- misc ----

def test_decode_lone_cr():
    assert decode_text(b"a\rb\r\nc") == "a\nb\nc"


def test_cors_preflight():
    r = client.options("/api/mask", headers={
        "Origin": "http://127.0.0.1:5500",
        "Access-Control-Request-Method": "POST",
    })
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] in ("*", "http://127.0.0.1:5500")


def test_health():
    assert client.get("/api/health").json() == {"ok": True}
