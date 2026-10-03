"""Light, dark or Auto: how Kosha looks in one browser."""

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from django.http import HttpRequest

COOKIE = "theme"
# Browsers cap a cookie's life at 400 days.
LASTS = 400 * 24 * 60 * 60


class Theme(NamedTuple):
    """A way Kosha can look."""

    value: str
    label: str
    icon: str


AUTO = Theme("auto", "Auto", "sun-moon")
THEMES = [AUTO, Theme("light", "Light", "sun"), Theme("dark", "Dark", "moon")]


def chosen(request: HttpRequest) -> Theme:
    """The theme this browser chose, or Auto if it chose none.

    Args:
        request: The incoming request.

    Returns:
        The theme.
    """
    return find(request.COOKIES.get(COOKIE)) or AUTO


def find(value: str | None) -> Theme | None:
    """The theme with a value.

    Args:
        value: Such as ``dark``.

    Returns:
        The theme, or None if there's none with that value.
    """
    return next((t for t in THEMES if t.value == value), None)
