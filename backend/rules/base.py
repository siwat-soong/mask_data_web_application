import re
from dataclasses import dataclass
from typing import Callable

@dataclass
class Rule:
    type: str
    pattern: re.Pattern
    mask: Callable[[re.Match], tuple[str, int]]   # (masked_text, chars_masked)
    near_miss: re.Pattern | None
    priority: int