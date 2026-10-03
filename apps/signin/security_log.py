"""Writing the Security log."""

from typing import TYPE_CHECKING

from apps.signin import client
from apps.signin.models import SecurityLogEntry

if TYPE_CHECKING:
    from django.http import HttpRequest

Kind = SecurityLogEntry.Kind


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


def failed(request: HttpRequest, kind: Kind) -> None:
    """Log a wrong password or code, unless it began a Pause.

    The Pause has its own entry, which says as much.

    Args:
        request: The request with the wrong try.
        kind: Which try was wrong.
    """
    if not getattr(request, "axes_locked_out", False):
        record(request, kind)
