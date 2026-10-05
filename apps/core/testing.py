"""Helpers shared by every app's tests."""

import re
from html import unescape
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


def chosen(response: HttpResponse) -> list[str]:
    """The options a page's selects have chosen.

    Args:
        response: The page.

    Returns:
        Each chosen option's value.
    """
    return [o["value"] for o in tags(response, "option") if "selected" in o]


def shown_history(response: HttpResponse) -> list[str]:
    """Each History entry's text, without the time it happened.

    Args:
        response: The History page.

    Returns:
        Each entry's text, newest first.
    """
    entries = re.findall(r"data-history-entry>(.*?)</li>", response.text, re.DOTALL)
    texts = (" ".join(re.sub(r"<[^>]+>", " ", e).split()) for e in entries)
    return [unescape(re.sub(r" \d+:\d\d [ap]m$", "", t)) for t in texts]
