# backend/rules/phone.py
import re
from .base import Rule

PATTERN = re.compile(r"(?<![\d-])\d{3}-\d{3}-(\d{4})(?![\d-])")
NEAR_MISS = re.compile(r"(?<![\d-])0\d{9}(?![\d-])")   # 10 digits, no dashes

def mask(m: re.Match) -> tuple[str, int]:
    return "XXX-XXX-" + m.group(1), 6

RULE = Rule("phone", PATTERN, mask, NEAR_MISS, priority=0)