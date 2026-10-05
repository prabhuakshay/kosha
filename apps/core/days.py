"""Grouping what happened under the day it happened."""

from datetime import timedelta
from itertools import groupby
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.formats import date_format

from apps.core import time_zone

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from datetime import datetime


def by_day[T](
    entries: Iterable[T], at: Callable[[T], datetime]
) -> list[tuple[str, list[T]]]:
    """Group entries, already newest first, under the day each happened.

    Args:
        entries: What to group, newest first.
        at: When an entry happened.

    Returns:
        Each day's name, such as ``Today`` or ``28 Sep 2026``, and its entries.
    """
    today = time_zone.today()
    names = {today: "Today", today - timedelta(days=1): "Yesterday"}
    days = groupby(entries, key=lambda e: timezone.localdate(at(e)))
    return [
        (names.get(day) or date_format(day, "j M Y"), list(group))
        for day, group in days
    ]
