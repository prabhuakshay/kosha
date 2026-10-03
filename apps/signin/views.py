"""Signing in and out."""

from typing import TYPE_CHECKING

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import reverse

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class SignInView(auth_views.LoginView):
    """Email and password. A signed-in Owner goes straight home."""

    template_name = "signin/sign_in.html"
    redirect_authenticated_user = True


@login_not_required
def admin_login(request: HttpRequest) -> HttpResponse:
    """Send the admin's own sign-in to Kosha's, so it has only one way in.

    Args:
        request: The incoming request.

    Returns:
        A redirect to Kosha's sign-in, coming back to the admin after.
    """
    return auth_views.redirect_to_login(request.GET.get("next", reverse("admin:index")))
