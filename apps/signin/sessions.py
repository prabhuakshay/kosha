"""Every browser signed in as the Owner."""

from typing import TYPE_CHECKING

from django.contrib.sessions.models import Session

if TYPE_CHECKING:
    from django.http import HttpRequest


def sign_out_others(request: HttpRequest) -> None:
    """Sign out every Session but this one.

    Args:
        request: The request whose Session stays signed in.
    """
    # The Owner is the only login, so every other session is theirs.
    Session.objects.exclude(session_key=request.session.session_key).delete()
