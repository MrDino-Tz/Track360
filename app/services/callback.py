from datetime import datetime, timezone
from typing import Any

from fastapi import Request


CALLBACK_KEYS = ("from", "to", "text", "id", "date", "linkId", "networkCode")


async def parse_africastalking_payload(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    data: dict[str, Any] = {}

    if "application/json" in content_type:
        body = await request.json()
        if isinstance(body, dict):
            data.update(body)
    else:
        form = await request.form()
        data.update({key: form.get(key) for key in form.keys()})

    for key, value in request.query_params.items():
        data.setdefault(key, value)

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        normalized[key] = str(value).strip()
    return normalized


def parse_callback_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    cleaned = value.replace("+", " ").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)
