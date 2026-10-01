# backend/rules/credit_card.py
import re
from .base import Rule

PATTERN = re.compile(r"(?<![\d-])(?:\d{4}-){3}(\d{4})(?![\d-])")
NEAR_MISS = re.compile(r"(?<![\d-])(?:\d{4} \d{4} \d{4} \d{4}|\d{13,19})(?![\d-])")   # spaces, no dashes, or wrong digit count

def mask(m: re.Match) -> tuple[str, int]:
    return "XXXX-XXXX-XXXX-" + m.group(1), 12

RULE = Rule("credit_card", PATTERN, mask, NEAR_MISS, priority=3)
