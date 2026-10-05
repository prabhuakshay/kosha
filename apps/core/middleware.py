"""Middleware shared across the project."""

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.cache import add_never_cache_headers

from apps.core import time_zone

if TYPE_CHECKING:
    from collections.abc import Callable

HEALTH_PATH = "/healthz/"


class HealthCheckMiddleware:
    """Answer ``/healthz/`` before any other middleware runs.

    It must sit first: the probe comes from inside the container over plain
    HTTP with a Host header ``ALLOWED_HOSTS`` rejects, which host validation
    and the HTTPS redirect would otherwise turn into failures.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Answer a health probe, or pass any other request on.

        Args:
            request: The incoming request.

        Returns:
            200 if the database answers, 503 if not, or the downstream response.
        """
        if request.path != HEALTH_PATH:
            return self.get_response(request)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            return HttpResponse(
                "database unavailable", status=HTTPStatus.SERVICE_UNAVAILABLE
            )
        return HttpResponse("ok")


class NoStoreMiddleware:
    """Keep every page out of the browser's caches unless it sets its own.

    Each page is private, and Back must ask the server again, so it can't show
    a finished sign-in step, codes shown once, or anything after signing out.
    Sits after WhiteNoise, so static files keep their long caching.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Mark the response no-store unless it says how to cache itself.

        Args:
            request: The incoming request.

        Returns:
            The downstream response.
        """
        response = self.get_response(request)
        if not response.has_header("Cache-Control"):
            add_never_cache_headers(response)
        return response


class TimeZoneMiddleware:
    """Show every date and time in the Owner's Time zone.

    The first time the Owner is fully signed in without one, it's guessed from
    the browser. A password alone may be a stranger's, so it can't set it. Runs
    after django-otp's ``OTPMiddleware``.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Answer the request in the Time zone.

        Args:
            request: The incoming request.

        Returns:
            The downstream response.
        """
        owner = request.user
        if owner.is_authenticated and owner.is_verified():
            time_zone.guess(request)
        with timezone.override(time_zone.current()):
            return self.get_response(request)
