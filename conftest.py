"""Project-wide test fixtures."""

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from django.utils import timezone

from apps.core.testing import EMAIL, PASSWORD

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
def signed_in(client, owner):
    client.force_login(owner)
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
