"""Helpers shared by every app's tests."""

import re
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


def sub_links(response: HttpResponse, container: str) -> list[str]:
    """The hrefs of the rail's section links inside one element.

    Args:
        response: A response with an HTML body.
        container: An attribute that marks the element, such as ``id="x"``.

    Returns:
        Each link's href, in order.
    """
    start = response.text.index(container)
    inside = response.text[start : response.text.index("</div>", start)]
    return re.findall(r'<a href="([^"]+)" class="sub-link"', inside)
