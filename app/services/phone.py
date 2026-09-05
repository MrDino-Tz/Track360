import re

from app.config import get_settings


_NON_DIGIT = re.compile(r"[^\d+]")


def normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    value = _NON_DIGIT.sub("", str(raw).strip())
    if not value:
        return ""
    if value.startswith("00"):
        value = "+" + value[2:]
    if value.startswith("+"):
        return value
    settings = get_settings()
    if value.startswith("0"):
        return f"+{settings.default_phone_country_code}{value[1:]}"
    if len(value) <= 9:
        return f"+{settings.default_phone_country_code}{value}"
    return f"+{value}"
