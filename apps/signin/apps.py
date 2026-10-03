"""App configuration for signin."""

from typing import override

from django.apps import AppConfig


class SigninConfig(AppConfig):
    """Configuration for the signin app."""

    name = "apps.signin"

    @override
    def ready(self) -> None:
        """Connect to the signals that a Pause began and that a Session signed in."""
        from apps.signin import pause, sessions  # ruff: ignore[unused-import, import-outside-top-level]
