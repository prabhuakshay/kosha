"""The Pause: an address that got too many passwords or codes wrong waits an hour.

django-axes counts wrong passwords itself; wrong codes are counted here, against
the same address.
"""

from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING

from axes.handlers.proxy import AxesProxyHandler
from axes.models import AccessAttempt
from axes.signals import user_locked_out
from django.conf import settings
from django.contrib.auth.signals import user_login_failed
from django.db.models import Max
from django.dispatch import receiver
from django.shortcuts import render

from apps.signin import client, security_log

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

    from apps.users.models import User


def paused_page(
    request: HttpRequest,
    original_response: HttpResponse | None = None,  # ruff: ignore[unused-function-argument]
    credentials: dict | None = None,  # ruff: ignore[unused-function-argument]
) -> HttpResponse:
    """Say signing in is paused, and until when.

    django-axes calls this when a wrong try begins a Pause.

    Args:
        request: The incoming request.
        original_response: The response it replaces (unused).
        credentials: What was tried (unused).

    Returns:
        The paused page.
    """
    # Every count's last try is when the Pause began.
    last_try = AccessAttempt.objects.filter(
        ip_address=client.address(request)
    ).aggregate(at=Max("attempt_time"))["at"]
    return render(
        request,
        "signin/paused.html",
        {
            "failure_limit": settings.AXES_FAILURE_LIMIT,
            "until": last_try and last_try + settings.AXES_COOLOFF_TIME,
        },
        status=HTTPStatus.TOO_MANY_REQUESTS,
    )


# Sent once per Pause: every way to sign in refuses a paused address before
# django-axes sees another try.
@receiver(user_locked_out)
def _pause_began(request: HttpRequest, **_: object) -> None:
    # django-axes keeps a count per browser at an address, each ageing out an
    # hour after its own last try, so an older one would end the Pause early.
    AccessAttempt.objects.filter(ip_address=request.axes_ip_address).update(
        attempt_time=request.axes_attempt_time
    )
    security_log.record(request, security_log.Kind.PAUSED)


def refused_while_paused(view: Callable) -> Callable:
    """Show the paused page instead of this view while the address is paused.

    Returns:
        The view, wrapped.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not AxesProxyHandler.is_allowed(request):
            return paused_page(request)
        return view(request, *args, **kwargs)

    return wrapper


def wrong_code(request: HttpRequest, owner: User) -> None:
    """Count a wrong Authenticator or Recovery code against the address, and log it.

    Args:
        request: The request with the wrong code.
        owner: Whose code it was meant to be.
    """
    user_login_failed.send(
        sender=__name__,
        credentials={"username": owner.get_username()},
        request=request,
    )
    security_log.failed(request, security_log.Kind.WRONG_CODE)
