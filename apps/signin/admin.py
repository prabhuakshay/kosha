"""The Security log, readable in the admin but never editable."""

from typing import TYPE_CHECKING, override

from django.contrib import admin

from apps.signin.models import SecurityLogEntry

if TYPE_CHECKING:
    from django.http import HttpRequest


@admin.register(SecurityLogEntry)
class SecurityLogEntryAdmin(admin.ModelAdmin):
    """Read-only, so an intruder can't cover their tracks from Kosha."""

    list_display = ("at", "kind", "detail", "address", "device")
    list_filter = ("kind",)

    @override
    def has_add_permission(self, request: HttpRequest) -> bool:
        """Refuse adding entries by hand.

        Args:
            request: The incoming request.

        Returns:
            False.
        """
        return False

    @override
    def has_change_permission(
        self, request: HttpRequest, obj: SecurityLogEntry | None = None
    ) -> bool:
        """Refuse editing entries.

        Args:
            request: The incoming request.
            obj: The entry, or None for entries in general.

        Returns:
            False.
        """
        return False

    @override
    def has_delete_permission(
        self, request: HttpRequest, obj: SecurityLogEntry | None = None
    ) -> bool:
        """Refuse deleting entries.

        Args:
            request: The incoming request.
            obj: The entry, or None for entries in general.

        Returns:
            False.
        """
        return False
