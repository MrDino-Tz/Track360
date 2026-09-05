import logging

logger = logging.getLogger(__name__)

try:
    import africastalking

    _SDK_AVAILABLE = True
except ImportError:
    africastalking = None  # type: ignore[assignment]
    _SDK_AVAILABLE = False
    logger.warning("africastalking SDK not installed — outbound SMS disabled")

from app.config import get_settings


def _init_sdk() -> None:
    if not _SDK_AVAILABLE:
        return
    settings = get_settings()
    username = settings.africastalking_username
    api_key = settings.africastalking_api_key

    if settings.africastalking_sandbox:
        username = "sandbox"

    if not username or not api_key:
        logger.warning("Africa's Talking SDK not initialised: username and/or API key are not set")
        return

    africastalking.initialize(username, api_key)


def get_airtime():
    if not _SDK_AVAILABLE:
        return None
    if africastalking.Airtime is None:
        _init_sdk()
    return africastalking.Airtime


def get_sms():
    if not _SDK_AVAILABLE:
        return None
    if africastalking.SMS is None:
        _init_sdk()
    return africastalking.SMS
