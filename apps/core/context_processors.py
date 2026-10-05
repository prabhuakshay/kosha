"""What every page's shell needs to know."""

from typing import TYPE_CHECKING

from apps.core import appearance

if TYPE_CHECKING:
    from django.http import HttpRequest

# Settings' pages come from more than one app, so share no URL namespace.
SETTINGS_PAGES = {
    "settings",
    "base_currency",
    "history",
    "appearance",
    "security",
    "password",
    "new_authenticator",
    "new_recovery_codes",
    "confirm",
    "sessions",
    "security_log",
}


def section(request: HttpRequest) -> dict[str, str | None]:
    """Name the part of the app the page is in, for the side bar and tab bar.

    Args:
        request: The incoming request.

    Returns:
        ``section``: ``home``, ``accounts``, ``categories``, ``tags``,
        ``settings`` or None.
    """
    match = request.resolver_match
    name = match.view_name if match else ""
    if not name.startswith("masters:"):
        section = "home" if name == "home" else None
        if name in SETTINGS_PAGES:
            section = "settings"
    elif "categor" in name:
        section = "categories"
    elif "tag" in name:
        section = "tags"
    else:
        section = "accounts"
    return {"section": section}


def theme(request: HttpRequest) -> dict[str, appearance.Theme]:
    """Say which theme to draw the page in.

    Args:
        request: The incoming request.

    Returns:
        ``theme``: the theme this browser chose.
    """
    return {"theme": appearance.chosen(request)}
