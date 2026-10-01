# backend/rules/address.py
import re
from .base import Rule

PATTERN = re.compile(r"(Address:[ \t]*)(\d+(?:/\d+)?)")
NEAR_MISS = re.compile(r"Address:[ \t]*\S*", re.IGNORECASE)   # no house number, or wrong label case

def mask(m: re.Match) -> tuple[str, int]:
    house_number = m.group(2)
    return m.group(1) + re.sub(r"\d", "X", house_number), len(re.findall(r"\d", house_number))

RULE = Rule("address", PATTERN, mask, NEAR_MISS, priority=0)
