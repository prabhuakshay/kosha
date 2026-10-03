"""Project-wide test fixtures."""

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp_webauthn.helpers import WebAuthnHelper
from django_otp_webauthn.models import WebAuthnCredential

from apps.core.testing import EMAIL, PASSWORD
from apps.signin.testing import add_passkey, authenticator_code, enter_code

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper


# Applied to every test by `usefixtures` in pyproject.toml.
@pytest.fixture
def test_settings(settings: SettingsWrapper) -> None:
    # The hashed storage needs `collectstatic` to have run; tests only need URLs.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
    # The test client speaks plain HTTP, which production redirects to HTTPS.
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_superuser(EMAIL, PASSWORD, name="Asha Rao")


@pytest.fixture
def signed_in(client, owner, authenticator):
    """A client signed in as the Owner, past the code step."""
    client.force_login(owner)
    enter_code(client, authenticator_code(authenticator.bin_key))
    return client


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> object:
    """Freeze `timezone.now`, moving only when a test advances it.

    Returns:
        The clock: read `now`, call `advance(**timedelta_kwargs)`.
    """

    class Clock:
        now = timezone.now()

        def advance(self, **delta: float) -> None:
            self.now += timedelta(**delta)

    c = Clock()
    monkeypatch.setattr(timezone, "now", lambda: c.now)
    return c


@pytest.fixture
def authenticator(owner):
    return TOTPDevice.objects.create(user=owner, name="Authenticator app")


@pytest.fixture
def browser(monkeypatch):
    """Stand in for the browser and authenticator, which no test can run.

    Registering makes a new Passkey; signing in answers with the Owner's first.
    """
    monkeypatch.setattr(
        WebAuthnHelper,
        "register_complete",
        lambda self, user, **kwargs: add_passkey(user),
    )
    monkeypatch.setattr(
        WebAuthnHelper,
        "authenticate_complete",
        lambda self, **kwargs: WebAuthnCredential.objects.first(),
    )
