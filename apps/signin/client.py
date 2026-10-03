"""Where a request comes from: its address and the device that sent it."""

import re
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.http import HttpRequest

# First match wins, so Edge and Opera come before the Chrome they claim to be,
# and Chrome before the Safari it claims to be.
BROWSERS = [
    ("Edge", r"Edg(e|A|iOS)?/"),
    ("Opera", r"OPR/"),
    ("Samsung Internet", r"SamsungBrowser/"),
    ("Firefox", r"Firefox/|FxiOS/"),
    ("Chrome", r"Chrome/|CriOS/"),
    ("Safari", r"Safari/"),
]
SYSTEMS = [
    ("iPhone", r"iPhone"),
    ("iPad", r"iPad"),
    ("Android", r"Android"),
    ("macOS", r"Macintosh"),
    ("Windows", r"Windows"),
    ("ChromeOS", r"CrOS"),
    ("Linux", r"Linux"),
]


def address(request: HttpRequest) -> str:
    """The client's address.

    Behind the proxy, it's the last address in X-Forwarded-For: the one the
    proxy added. Any before it were sent by the client and can't be trusted.

    Args:
        request: The incoming request.

    Returns:
        The address, or an empty string when there is none.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if settings.USE_X_FORWARDED_FOR and forwarded:
        return forwarded.rsplit(",", 1)[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def device(request: HttpRequest) -> str:
    """Name the device a request came from the way the Owner would know it.

    Versions are left out, so a browser update isn't a new device.

    Args:
        request: The incoming request.

    Returns:
        Such as ``Safari on iPhone``, or ``Unknown device``.
    """
    user_agent = request.headers.get("User-Agent", "")
    browser = next((name for name, p in BROWSERS if re.search(p, user_agent)), "")
    system = next((name for name, p in SYSTEMS if re.search(p, user_agent)), "")
    if browser and system:
        return f"{browser} on {system}"
    return browser or system or "Unknown device"
