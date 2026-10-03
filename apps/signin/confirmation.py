"""Confirmation: a fresh Passkey or Authenticator app check, good for 10 minutes.

Every Security screen and change needs one. Finishing a sign-in opens one too,
even by Recovery code, so an Owner who lost their Authenticator app can set up
another.
"""

from datetime import timedelta
from functools import wraps
from typing import TYPE_CHECKING

from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
from django.utils import timezone

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

LASTS = timedelta(minutes=10)
UNTIL = "signin.confirmed_until"


def start(request: HttpRequest) -> None:
    """Open a Confirmation for the next 10 minutes.

    Args:
        request: The request that confirmed it's the Owner.
    """
    request.session[UNTIL] = (timezone.now() + LASTS).timestamp()


def is_open(request: HttpRequest) -> bool:
    """Whether the Owner confirmed it's them in the last 10 minutes.

    Args:
        request: The incoming request.

    Returns:
        True while the Confirmation lasts.
    """
    return timezone.now().timestamp() < request.session.get(UNTIL, 0)


def required(view: Callable) -> Callable:
    """Ask the Owner to confirm it's them before this view, unless they just did.

    Returns:
        The view, wrapped.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if is_open(request):
            return view(request, *args, **kwargs)
        # A form posted here can't be replayed after confirming; Security can.
        target = (
            request.get_full_path() if request.method == "GET" else reverse("security")
        )
        return redirect_to_login(target, "confirm")

    return wrapper
