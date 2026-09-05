import re

_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("LEAK", re.compile(r"\b(leak|leaking|spill|burst)\b", re.I)),
    ("OVERHEATING", re.compile(r"\b(overheat|overheating|hot|temperature|burning)\b", re.I)),
    ("STOPPAGE", re.compile(r"\b(stop|stopped|stuck|jammed|down|halted|not running|not working)\b", re.I)),
    ("ELECTRICAL", re.compile(r"\b(electric|electrical|power|trip|tripped|voltage)\b", re.I)),
    ("MECHANICAL", re.compile(r"\b(motor|belt|bearing|gear|shaft|conveyor|noise|noisy)\b", re.I)),
]


def classify_message(message: str) -> str | None:
    if not message:
        return None
    for category, pattern in _RULES:
        if pattern.search(message):
            return category
    return None
