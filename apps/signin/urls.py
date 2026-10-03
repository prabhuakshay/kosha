"""Signing in and out."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from apps.signin import views

urlpatterns = [
    path("sign-in/", login_not_required(views.SignInView.as_view()), name="sign_in"),
    # Public so a page left open past its sign-in can still sign out cleanly.
    path(
        "sign-out/",
        login_not_required(auth_views.LogoutView.as_view()),
        name="sign_out",
    ),
]
