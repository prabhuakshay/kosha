"""Hold a session that has only passed the password until it finishes signing in."""

from typing import TYPE_CHECKING

from django.contrib.auth.views import redirect_to_login
from django.utils.deprecation import MiddlewareMixin

from apps.signin import ways

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


def part_of_signing_in[V: Callable](view: V) -> V:
    """Let a session that has only passed the password reach this view.

    Such a session may be someone holding only a stolen password, so a marked
    view must never change a Way to sign in once the Owner has one.

    Returns:
        The view, marked.
    """
    view.part_of_signing_in = True
    return view


class WayToSignInMiddleware(MiddlewareMixin):
    """Send a session that has only passed the password on to the code step.

    An Owner with no Way to sign in is sent to set one up instead. Runs after
    ``LoginRequiredMiddleware`` and django-otp's ``OTPMiddleware``.
    """

    def process_view(  # ruff: ignore[no-self-use]
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: object,  # ruff: ignore[unused-method-argument]
        view_kwargs: object,  # ruff: ignore[unused-method-argument]
    ) -> HttpResponse | None:
        """Redirect a session that hasn't finished signing in.

        Args:
            request: The incoming request.
            view_func: The view about to run.
            view_args: Its positional arguments (unused).
            view_kwargs: Its keyword arguments (unused).

        Returns:
            A redirect, or None to let the request through.
        """
        owner = request.user
        if not owner.is_authenticated or owner.is_verified():
            return None
        if not getattr(view_func, "login_required", True):
            return None
        if getattr(view_func, "part_of_signing_in", False):
            return None
        target = "code_step" if ways.has_way_to_sign_in(owner) else "choose_way"
        return redirect_to_login(request.get_full_path(), target)
