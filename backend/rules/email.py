# backend/rules/email.py
import re
from .base import Rule

PATTERN = re.compile(r"([A-Za-z0-9._%+-]+)(@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
NEAR_MISS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]*")   # no dot in the domain, or no domain

def mask(m: re.Match) -> tuple[str, int]:
    user, domain = m.group(1), m.group(2)
    hidden = max(len(user) - 2, 0)   # 1-2 letter usernames have nothing between first and last
    if hidden == 0:
        return user + domain, 0
    return user[0] + "*" * hidden + user[-1] + domain, hidden

RULE = Rule("email", PATTERN, mask, NEAR_MISS, priority=1)
