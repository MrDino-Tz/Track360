"""Report rewards — send a motivational payout (airtime or mobile money) to the
reporter of an incident via Africa's Talking.

Airtime uses the official SDK (``africastalking.Airtime``); mobile money uses
the Payments B2C REST API directly (the installed SDK has no Payments module).
Both are sandbox-aware via the global Africa's Talking settings.
"""

import logging

import httpx

from app.config import get_settings
from app.services.africastalking import _SDK_AVAILABLE, get_airtime

logger = logging.getLogger(__name__)

MIN_AMOUNT = 100
DEFAULT_CURRENCY = "TZS"

SUCCESS_STATUSES = {"success", "sent", "queued", "accepted"}


def _airtime_entry(response):
    if isinstance(response, dict):
        responses = response.get("responses") or []
        return responses[0] if responses else None
    return None


def send_airtime(phone: str, amount: int | float) -> dict:
    """Send mobile airtime to ``phone``. Returns a normalized result dict."""
    if not _SDK_AVAILABLE:
        return _fail("africastalking SDK not installed")
    airtime = get_airtime()
    if airtime is None:
        return _fail("Africa's Talking SDK not initialised (username/API key missing)")

    try:
        response = airtime.send(
            phone_number=phone,
            amount=str(amount),
            currency_code=DEFAULT_CURRENCY,
            max_num_retry=1,
        )
    except Exception as exc:
        logger.error("Airtime reward to %s failed: %s", phone, exc)
        return _fail(str(exc))

    entry = _airtime_entry(response)
    if entry is None:
        return {
            "ok": True,
            "provider_status": "QUEUED",
            "provider_reference": None,
            "message": str(response),
        }

    status = str(entry.get("status") or "QUEUED")
    return {
        "ok": status.strip().lower() in SUCCESS_STATUSES,
        "provider_status": status,
        "provider_reference": entry.get("requestId") or entry.get("id"),
        "message": entry.get("errorMessage") or str(entry),
    }


def send_mobile_money(phone: str, amount: int | float) -> dict:
    """Send a mobile-money (B2C) payout to ``phone`` via Africa's Talking Payments."""
    settings = get_settings()
    if not settings.africastalking_payments_product_name:
        return _fail(
            "AFRICASTALKING_PAYMENTS_PRODUCT_NAME is not set — configure it in the "
            "Africa's Talking dashboard to enable mobile-money rewards",
            provider_status="UNCONFIGURED",
        )

    host = "https://payments.africastalking.com"
    if settings.africastalking_sandbox:
        host = "https://payments.sandbox.africastalking.com"
    username = (
        "sandbox" if settings.africastalking_sandbox else settings.africastalking_username
    )

    payload = {
        "username": username,
        "productName": settings.africastalking_payments_product_name,
        "recipients": [
            {
                "phoneNumber": phone,
                "currencyCode": DEFAULT_CURRENCY,
                "amount": float(amount),
                "reason": "Motivational reward for incident report",
                "metadata": {"kind": "incident-report-reward"},
            }
        ],
    }
    headers = {
        "apiKey": settings.africastalking_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = httpx.post(f"{host}/mobile/b2c/request", json=payload, headers=headers, timeout=15.0)
        data = resp.json() if resp.content else {}
    except Exception as exc:
        logger.error("Mobile-money reward to %s failed: %s", phone, exc)
        return _fail(str(exc))

    if resp.status_code >= 400:
        msg = data.get("message") or str(data)
        logger.error("B2C reward to %s rejected (%s): %s", phone, resp.status_code, msg)
        return _fail(msg, provider_status=f"HTTP {resp.status_code}")

    entries = data.get("entries") or []
    if entries:
        entry = entries[0]
        status = str(entry.get("status") or "QUEUED")
        return {
            "ok": status.strip().lower() in SUCCESS_STATUSES,
            "provider_status": status,
            "provider_reference": entry.get("transactionId"),
            "message": str(data),
        }

    return {
        "ok": True,
        "provider_status": "QUEUED",
        "provider_reference": data.get("transactionId"),
        "message": str(data),
    }


def _fail(message: str, provider_status: str = "FAILED") -> dict:
    return {
        "ok": False,
        "provider_status": provider_status,
        "provider_reference": None,
        "message": message,
    }