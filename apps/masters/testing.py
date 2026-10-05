"""Helpers for tests that add and edit Masters, as the Owner would."""

import re
from html import unescape
from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.timezone import localdate

from apps.core.testing import tags
from apps.masters.listings import LISTINGS
from apps.masters.models import KINDS, Account, Category, Tag

if TYPE_CHECKING:
    from django.http import HttpResponse
    from django.test import Client

FILLED_IN = {
    Account.Type.ASSET: {"name": "HDFC Savings", "kind": "bank"},
    Account.Type.LIABILITY: {"name": "HDFC Regalia", "kind": "credit_card"},
    Account.Type.EXPENSE: {"name": "Amazon"},
    Account.Type.INCOME: {"name": "Acme Corp"},
}


def add(
    client: Client, type_: Account.Type = Account.Type.ASSET, **fields: str
) -> HttpResponse:
    """Submit the new Account form for a type, filled in except for ``fields``.

    Args:
        client: A signed-in client.
        type_: The Account's type.
        **fields: Values to submit in place of the defaults.

    Returns:
        The response.
    """
    data = {**FILLED_IN[type_], "notes": ""}
    if type_ in KINDS:
        data |= {"opening_balance": "0", "opened_on": localdate().isoformat()}
    data |= fields
    return client.post(reverse(LISTINGS[type_].new), data)


def edit(client: Client, account: Account, **fields: str) -> HttpResponse:
    """Submit an Account's edit form, changing only ``fields``.

    Args:
        client: A signed-in client.
        account: The Account.
        **fields: Values to submit in place of its own.

    Returns:
        The response.
    """
    data = {"name": account.name, "notes": account.notes}
    if account.type in KINDS:
        data |= {
            "kind": account.kind,
            "opening_balance": str(account.opening_balance),
            "opened_on": account.opened_on.isoformat(),
        }
    data |= fields
    return client.post(reverse(LISTINGS[account.type].edit, args=[account.pk]), data)


def errors(response: HttpResponse) -> list[str]:
    """The errors a form shows under its fields.

    Args:
        response: The form's page.

    Returns:
        Each error's text.
    """
    found = re.findall(r'<span class="field-error block">([^<]+)', response.text)
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
        r'data-kind>([^<]+)</span><span [^>]*data-subtotal="\w+">([^<]+)<',
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
        r'data-name>([^<]+)</span></span>\s*<span class="row-value amount" '
        r"data-balance>([^<]+)<",
        response.text,
    )


def history(response: HttpResponse) -> tuple[list[str], list[str]]:
    """What an Account's History says, as its detail pane shows it.

    Args:
        response: The Account's detail.

    Returns:
        Each entry's action, and each changed field written out.
    """
    actions = re.findall(r"data-history-action>([^<]+)<", response.text)
    changes = re.findall(r"data-history-change>([^<]+)<", response.text)
    return actions, [unescape(c) for c in changes]


def account(
    type_: Account.Type, name: str = "HDFC", balance: int = 0, *, closed: bool = False
) -> Account:
    """Make an Account straight in the database, with a Kind if its type has them.

    Args:
        type_: The Account's type.
        name: Its name.
        balance: Its Opening balance, if its type has one.
        closed: Whether it's Closed.

    Returns:
        The Account.
    """
    if type_ not in KINDS:
        return Account.objects.create(type=type_, name=name, closed=closed)
    return Account.objects.create(
        type=type_,
        kind=FILLED_IN[type_]["kind"],
        name=name,
        opening_balance=balance,
        opened_on=localdate(),
        closed=closed,
    )


def url(action: str, account: Account) -> str:
    """The address of an Account's detail, or of an action on it.

    Args:
        action: A route prefix such as ``close_``, or nothing for the detail.
        account: The Account.

    Returns:
        The address.
    """
    return reverse(f"masters:{action}{LISTINGS[account.type].route}", args=[account.pk])


def listed(client: Client, type_: Account.Type) -> tuple[list[str], list[str]]:
    """The names in a list of Accounts.

    Args:
        client: A signed-in client.
        type_: The list's type.

    Returns:
        The open Accounts' names, then those in the Closed section.
    """
    text = client.get(reverse("masters:accounts")).text
    open_part, _, closed_part = text.partition("data-closed")
    start = open_part.index(f'id="{LISTINGS[type_].plural}"')
    end = open_part.find('class="sec sec-lead" id=', start)
    return names(open_part[start : end if end != -1 else None]), names(closed_part)


def listed_at(client: Client, address: str) -> tuple[list[str], list[str]]:
    """The names in a list in Masters.

    Args:
        client: A signed-in client.
        address: The list's address.

    Returns:
        The open ones' names, then those in the Closed section.
    """
    text = client.get(address).text
    open_part, _, closed_part = text.partition("data-closed")
    return names(open_part), names(closed_part)


def names(part: str) -> list[str]:
    """The names of the things listed in part of a page.

    Args:
        part: Some of the page's HTML.

    Returns:
        Each name, in order.
    """
    return [unescape(n) for n in re.findall(r"data-name>([^<]+)<", part)]


def category(
    name: str = "Groceries",
    color: str = "forest",
    icon: str = "",
    *,
    closed: bool = False,
) -> Category:
    """Make a Category straight in the database.

    Args:
        name: Its name.
        color: Its palette color's key.
        icon: Its icon's key, if any.
        closed: Whether it's Closed.

    Returns:
        The Category.
    """
    return Category.objects.create(name=name, color=color, icon=icon, closed=closed)


def category_url(action: str, category: Category) -> str:
    """The address of a Category's detail, or of an action on it.

    Args:
        action: A route prefix such as ``close_``, or nothing for the detail.
        category: The Category.

    Returns:
        The address.
    """
    return reverse(f"masters:{action}category", args=[category.pk])


def tag(name: str = "Goa trip 2026") -> Tag:
    """Make a Tag straight in the database.

    Args:
        name: Its name.

    Returns:
        The Tag.
    """
    return Tag.objects.create(name=name)


def tag_url(action: str, tag: Tag) -> str:
    """The address of a Tag's detail, or of an action on it.

    Args:
        action: A route prefix such as ``delete_``, or nothing for the detail.
        tag: The Tag.

    Returns:
        The address.
    """
    return reverse(f"masters:{action}tag", args=[tag.pk])


def notices(response: HttpResponse) -> list[str]:
    """The notices a page shows after something was done, or refused.

    Args:
        response: The page.

    Returns:
        Each notice's text.
    """
    found = re.findall(r'role="status"><i[^>]*></i>([^<]+)<', response.text)
    return [unescape(n) for n in found]
