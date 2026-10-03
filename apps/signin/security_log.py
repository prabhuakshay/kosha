"""Writing and reading the Security log."""

import logging
from typing import TYPE_CHECKING

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from apps.core import days
from apps.signin import client
from apps.signin.models import SecurityLogEntry

if TYPE_CHECKING:
    from django.http import HttpRequest

Kind = SecurityLogEntry.Kind
logger = logging.getLogger(__name__)


def record(
    request: HttpRequest | None, kind: Kind, detail: str = ""
) -> SecurityLogEntry:
    """Add an entry to the Security log.

    Args:
        request: The request it happened in, for its address and device; None
            for what happens on the server.
        kind: What happened.
        detail: More about it, such as how a sign-in was made.

    Returns:
        The entry.
    """
    return SecurityLogEntry.objects.create(
        kind=kind,
        detail=detail,
        address=client.address(request)[:64] if request else "",
        device=client.device(request) if request else "",
    )


def signed_in(request: HttpRequest, how: str) -> None:
    """Log a finished sign-in, emailing the Owner when it came from somewhere new.

    Somewhere new is an address or device no earlier sign-in used. The first
    sign-in, at Claim, has nothing to compare with, so it sends nothing.

    Args:
        request: The request that signed in.
        how: How, such as ``Passkey``.
    """
    entry = record(request, Kind.SIGNED_IN, how)
    earlier = SecurityLogEntry.objects.filter(kind=Kind.SIGNED_IN).exclude(pk=entry.pk)
    if earlier.exists() and not (
        earlier.filter(address=entry.address).exists()
        and earlier.filter(device=entry.device).exists()
    ):
        _email_new_sign_in(request, entry)


def _email_new_sign_in(request: HttpRequest, entry: SecurityLogEntry) -> None:
    body = render_to_string(
        "signin/new_sign_in_email.txt",
        {
            "entry": entry,
            "sessions_url": request.build_absolute_uri(reverse("sessions")),
        },
    )
    try:
        send_mail("New sign-in to Kosha", body, None, [request.user.email])
    except Exception:
        # No failure to send, of any kind, may stop the Owner signing in.
        logger.exception("Couldn't email the Owner about a new sign-in")


def failed(request: HttpRequest, kind: Kind) -> None:
    """Log a wrong password or code, unless it began a Pause.

    The Pause has its own entry, which says as much.

    Args:
        request: The request with the wrong try.
        kind: Which try was wrong.
    """
    if not getattr(request, "axes_locked_out", False):
        record(request, kind)


def by_day() -> list[tuple[str, list[SecurityLogEntry]]]:
    """Every entry, newest first, under the day it happened.

    Returns:
        Each day's name, such as ``Today`` or ``28 Sep 2026``, and its entries.
    """
    return days.by_day(SecurityLogEntry.objects.all(), at=lambda e: e.at)
