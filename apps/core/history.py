"""Writing and reading History."""

from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType

from apps.core import days
from apps.core.models import HistoryEntry

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

Action = HistoryEntry.Action


def record(
    subject: Model,
    action: Action,
    *,
    type_: str,
    name: str,
    changes: list[list[str]] | None = None,
) -> HistoryEntry:
    """Add an entry to History, in the transaction that made the change.

    Args:
        subject: What changed.
        action: What happened to it.
        type_: What sort of thing it is, such as ``Asset account``.
        name: What it's called now.
        changes: Each changed field as ``[name, old, new]``.

    Returns:
        The entry.
    """
    return HistoryEntry.objects.create(
        action=action,
        subject_model=ContentType.objects.get_for_model(subject),
        subject_id=subject.pk,
        subject_type=type_,
        subject_name=name,
        changes=changes or [],
    )


def changes(before: dict[str, str], after: dict[str, str]) -> list[list[str]]:
    """The fields whose written-out value differs between two snapshots.

    Args:
        before: Each field's value before the change.
        after: Each field's value after it.

    Returns:
        Each changed field as ``[name, old, new]``.
    """
    return [
        [field, old, after[field]]
        for field, old in before.items()
        if old != after[field]
    ]


def of(subject: Model) -> QuerySet[HistoryEntry]:
    """A subject's own entries, newest first.

    Args:
        subject: The Account, Category, Tag or Setting.

    Returns:
        Its entries.
    """
    return HistoryEntry.objects.filter(
        subject_model=ContentType.objects.get_for_model(subject),
        subject_id=subject.pk,
    )


def by_day() -> list[tuple[str, list[HistoryEntry]]]:
    """Every entry, newest first, under the day it happened.

    Returns:
        Each day's name, such as ``Today`` or ``28 Sep 2026``, and its entries.
    """
    return days.by_day(HistoryEntry.objects.all(), at=lambda e: e.at)
