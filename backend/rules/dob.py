# backend/rules/dob.py
import re
from .base import Rule

PATTERN = re.compile(r"(DOB:[ \t]*)(?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])/(\d{2})\d{2}(?!\d)")
NEAR_MISS = re.compile(r"DOB:[ \t]*\d{1,2}[/.-]\d{1,2}[/.-]\d{1,4}", re.IGNORECASE)   # bad day/month, separator, year or label

def mask(m: re.Match) -> tuple[str, int]:
    return m.group(1) + "XX/XX/" + m.group(2) + "XX", 6

RULE = Rule("dob", PATTERN, mask, NEAR_MISS, priority=2)
