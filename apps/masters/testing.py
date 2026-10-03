"""Helpers for tests that add and edit Asset accounts, as the Owner would."""

from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.timezone import localdate

if TYPE_CHECKING:
    from django.http import HttpResponse
    from django.test import Client

    from apps.masters.models import Account


def add(client: Client, **fields: str) -> HttpResponse:
    """Submit the new Asset account form, filled in except for ``fields``.

    Args:
        client: A signed-in client.
        **fields: Values to submit in place of the defaults.

    Returns:
        The response.
    """
    data = {
        "name": "HDFC Savings",
        "kind": "bank",
        "opening_balance": "0",
        "opened_on": localdate().isoformat(),
        "notes": "",
        **fields,
    }
    return client.post(reverse("masters:new_asset"), data)


def edit(client: Client, account: Account, **fields: str) -> HttpResponse:
    """Submit an Asset account's edit form, changing only ``fields``.

    Args:
        client: A signed-in client.
        account: The Account.
        **fields: Values to submit in place of its own.

    Returns:
        The response.
    """
    data = {
        "name": account.name,
        "kind": account.kind,
        "opening_balance": str(account.opening_balance),
        "opened_on": account.opened_on.isoformat(),
        "notes": account.notes,
        **fields,
    }
    return client.post(reverse("masters:edit_asset", args=[account.pk]), data)
