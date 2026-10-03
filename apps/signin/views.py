"""Claiming the install, and signing in and out."""

from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.signin.claim import is_claimed
from apps.signin.forms import OwnerForm, SetupCodeForm

# Set once the Setup code is right, so step 2 can't be reached by URL.
CODE_ACCEPTED = "signin.setup_code_accepted"


def _unclaimed_only() -> None:
    if is_claimed():
        raise Http404


@login_not_required
def claim(request: HttpRequest) -> HttpResponse:
    """Step 1 of Claim: the Setup code from the server's log.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect to step 2 once the code is right.
    """
    _unclaimed_only()
    form = SetupCodeForm(request.POST or None)
    if form.is_valid():
        request.session[CODE_ACCEPTED] = True
        return redirect("claim_owner")
    return render(request, "signin/claim.html", {"form": form})


@login_not_required
def claim_owner(request: HttpRequest) -> HttpResponse:
    """Step 2 of Claim: the Owner's name, email and password.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect home signed in once the Owner exists.
    """
    _unclaimed_only()
    if not request.session.get(CODE_ACCEPTED):
        return redirect("claim")
    form = OwnerForm(request.POST or None)
    if form.is_valid():
        login(request, form.save())
        return redirect("home")
    return render(request, "signin/claim_owner.html", {"form": form})


class SignInView(auth_views.LoginView):
    """Email and password. A signed-in Owner goes straight home."""

    template_name = "signin/sign_in.html"
    redirect_authenticated_user = True

    def dispatch(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """Send an unclaimed install to Claim, since nobody can sign in yet.

        Args:
            request: The incoming request.
            *args: Positional URL arguments.
            **kwargs: Keyword URL arguments.

        Returns:
            The sign-in page, or a redirect to Claim.
        """
        if not is_claimed():
            return redirect("claim")
        return super().dispatch(request, *args, **kwargs)


@login_not_required
def admin_login(request: HttpRequest) -> HttpResponse:
    """Send the admin's own sign-in to Kosha's, so it has only one way in.

    Args:
        request: The incoming request.

    Returns:
        A redirect to Kosha's sign-in, coming back to the admin after.
    """
    return auth_views.redirect_to_login(request.GET.get("next", reverse("admin:index")))
