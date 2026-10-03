"""Helpers for tests that add and edit Accounts, as the Owner would."""

import re
from html import unescape
from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.timezone import localdate

from apps.core.testing import tags
from apps.masters.models import Account

if TYPE_CHECKING:
    from django.http import HttpResponse
    from django.test import Client

FILLED_IN = {
    Account.Type.ASSET: {"name": "HDFC Savings", "kind": "bank"},
    Account.Type.LIABILITY: {"name": "HDFC Regalia", "kind": "credit_card"},
}


def add(
    client: Client, type_: Account.Type = Account.Type.ASSET, **fields: str
) -> HttpResponse:
    """Submit the new Account form for a type, filled in except for ``fields``.

    Args:
        client: A signed-in client.
        type_: An Asset account or a Liability.
        **fields: Values to submit in place of the defaults.

    Returns:
        The response.
    """
    data = {
        **FILLED_IN[type_],
        "opening_balance": "0",
        "opened_on": localdate().isoformat(),
        "notes": "",
        **fields,
    }
    return client.post(reverse(f"masters:new_{type_}"), data)


def edit(client: Client, account: Account, **fields: str) -> HttpResponse:
    """Submit an Account's edit form, changing only ``fields``.

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
    return client.post(reverse(f"masters:edit_{account.type}", args=[account.pk]), data)


def errors(response: HttpResponse) -> list[str]:
    """The errors a form shows under its fields.

    Args:
        response: The form's page.

    Returns:
        Each error's text.
    """
    found = re.findall(
        r'<p class="mt-1.5 text-\[13px\] font-medium text-bad">([^<]+)', response.text
    )
    return [unescape(e) for e in found]


def field_value(response: HttpResponse, name: str) -> str | None:
    """The value a form's input shows.

    Args:
        response: The form's page.
        name: The input's name.

    Returns:
        Its value.
    """
    return tags(response, "input", name=name)[0]["value"]


def groups(response: HttpResponse) -> list[tuple[str, str]]:
    """Each Kind in a list of Accounts, with its subtotal.

    Args:
        response: The list's page.

    Returns:
        Each Kind's label and subtotal.
    """
    return re.findall(
        r'data-kind>([^<]+)</span><span class="amount" data-subtotal="\w+">([^<]+)<',
        response.text,
    )


def rows(response: HttpResponse) -> list[tuple[str, str]]:
    """Each Account in a list, with its balance.

    Args:
        response: The list's page.

    Returns:
        Each row's name and balance.
    """
    return re.findall(
        r'font-semibold">([^<]+)</span>\s*<span class="amount text-\[14px\]" '
        r"data-balance>([^<]+)<",
        response.text,
    )
