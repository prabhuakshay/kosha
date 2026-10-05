"""The Owner's Time zone, which decides what today is."""

from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, available_timezones

from django.conf import settings
from django.utils import timezone

from apps.core.models import Setting

if TYPE_CHECKING:
    from datetime import date

    from django.http import HttpRequest

# Set by app.js on every page, so the server can learn the browser's zone.
COOKIE = "time_zone"
# Leaves out names like "localtime" and "EST5EDT" that no browser reports.
ZONES = sorted(z for z in available_timezones() if "/" in z or z == "UTC")


def name() -> str:
    """The Time zone's name, or the server's until the Owner's is set.

    Returns:
        Such as ``Asia/Kolkata``.
    """
    return Setting.load().time_zone or settings.TIME_ZONE


def current() -> ZoneInfo:
    """The Time zone, or the server's until the Owner's is set.

    Returns:
        The zone.
    """
    return ZoneInfo(name())


def today() -> date:
    """What day it is now in the Time zone.

    Returns:
        Today.
    """
    return timezone.localdate(timezone=current())


def guess(request: HttpRequest) -> None:
    """Set the Time zone from the browser's, unless one is set already.

    Args:
        request: A request from the Owner's browser.
    """
    setting = Setting.load()
    zone = request.COOKIES.get(COOKIE)
    if not setting.time_zone and zone in ZONES:
        setting.time_zone = zone
        setting.save(update_fields=["time_zone"])
