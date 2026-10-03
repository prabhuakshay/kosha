"""The Security log, readable in the admin but never editable."""

from django.contrib import admin

from apps.core.admin import ReadOnlyAdmin
from apps.signin.models import SecurityLogEntry


@admin.register(SecurityLogEntry)
class SecurityLogEntryAdmin(ReadOnlyAdmin):
    """Read-only, so an intruder can't cover their tracks from Kosha."""

    list_display = ("at", "kind", "detail", "address", "device")
    list_filter = ("kind",)
