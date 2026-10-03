"""Admins for permanent records: History, and the base for the Security log."""

from typing import TYPE_CHECKING, override

from django.contrib import admin

from apps.core.models import HistoryEntry

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest


class ReadOnlyAdmin(admin.ModelAdmin):
    """An admin for a permanent record, so nobody can rewrite it from Kosha."""

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
        self, request: HttpRequest, obj: Model | None = None
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
        self, request: HttpRequest, obj: Model | None = None
    ) -> bool:
        """Refuse deleting entries.

        Args:
            request: The incoming request.
            obj: The entry, or None for entries in general.

        Returns:
            False.
        """
        return False


@admin.register(HistoryEntry)
class HistoryEntryAdmin(ReadOnlyAdmin):
    """History, read-only so it can be trusted."""

    list_display = ("at", "action", "subject_type", "subject_name", "changes")
    list_filter = ("action", "subject_type")
