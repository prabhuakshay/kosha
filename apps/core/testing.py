"""Helpers shared by every app's tests."""

from html.parser import HTMLParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpResponse

EMAIL = "owner@example.com"
PASSWORD = "a long harbour lantern"  # ruff: ignore[hardcoded-password-string]


class _Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def tags(
    response: HttpResponse, tag: str, /, **attrs: str
) -> list[dict[str, str | None]]:
    """Find the tags in a response with a name and attribute values.

    Args:
        response: A response with an HTML body.
        tag: The tag name, such as ``script``.
        **attrs: Attribute values every match must have.

    Returns:
        Each matching tag's attributes.
    """
    parser = _Tags()
    parser.feed(response.text)
    return [
        a
        for t, a in parser.tags
        if t == tag and all(a.get(k) == v for k, v in attrs.items())
    ]
