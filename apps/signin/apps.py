"""App configuration for signin."""

from typing import override

from django.apps import AppConfig


class SigninConfig(AppConfig):
    """Configuration for the signin app."""

    name = "apps.signin"

    @override
    def ready(self) -> None:
        """Connect to django-axes' signal that a Pause began."""
        from apps.signin import pause  # ruff: ignore[unused-import, import-outside-top-level]
