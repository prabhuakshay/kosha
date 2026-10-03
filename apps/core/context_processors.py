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
    """Name the section of the app rail the page is in, if any.

    Args:
        request: The incoming request.

    Returns:
        ``section``: ``masters``, ``settings`` or None.
    """
    match = request.resolver_match
    if match is None:
        return {"section": None}
    if match.namespace == "masters":
        return {"section": "masters"}
    return {"section": "settings" if match.view_name in SETTINGS_PAGES else None}


def theme(request: HttpRequest) -> dict[str, appearance.Theme]:
    """Say which theme to draw the page in.

    Args:
        request: The incoming request.

    Returns:
        ``theme``: the theme this browser chose.
    """
    return {"theme": appearance.chosen(request)}
