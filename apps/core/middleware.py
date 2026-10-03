"""Middleware shared across the project."""

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse

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
