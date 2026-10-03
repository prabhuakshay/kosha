"""Masters: the Accounts, Categories and Tags everything else refers to."""

from typing import TYPE_CHECKING

from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.formats import date_format

from apps.core import history
from apps.core.money import write
from apps.masters.forms import AssetAccountForm
from apps.masters.models import Account

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

# Lists still to come: what belongs in each, for their empty states.
COMING = {
    "liabilities": (
        "Liabilities",
        "credit-card",
        "Money you owe: credit cards, loans, a mortgage and debts to people.",
    ),
    "income": (
        "Income",
        "arrow-down-left",
        "Income accounts: who pays you, such as an employer, a client or a tenant.",
    ),
    "expenses": (
        "Expenses",
        "arrow-up-right",
        "Expense accounts: who you pay, such as a shop, a landlord or a utility.",
    ),
    "categories": (
        "Categories",
        "shapes",
        "What money is spent or received for, such as Groceries or Salary.",
    ),
    "tags": (
        "Tags",
        "tag",
        "The context money moves in, such as a trip or “reimbursable”.",
    ),
}


def masters(request: HttpRequest) -> HttpResponse:
    """List the lists in Masters, each with how many it holds and their total.

    Args:
        request: The incoming request.

    Returns:
        The Masters index.
    """
    accounts = list(Account.objects.all())

    def of(type_: Account.Type) -> list[Account]:
        return [a for a in accounts if a.type == type_]

    return render(
        request,
        "masters/masters.html",
        {
            "assets": summary(of(Account.Type.ASSET), total=True),
            "liabilities": summary(of(Account.Type.LIABILITY), total=True),
            "income": summary(of(Account.Type.INCOME)),
            "expenses": summary(of(Account.Type.EXPENSE)),
        },
    )


def summary(accounts: list[Account], *, total: bool = False) -> str:
    """Say how many Accounts a list holds, and what they hold between them.

    Args:
        accounts: The list's Accounts.
        total: Whether to add up their balances.

    Returns:
        Such as ``2 · ₹3,20,000.00``, or ``None yet``.
    """
    if not accounts:
        return "None yet"
    if total:
        return f"{len(accounts)} · {write(sum(a.balance for a in accounts))}"
    return str(len(accounts))


def coming(request: HttpRequest, name: str) -> HttpResponse:
    """Say what belongs in a list that can't be filled yet.

    Args:
        request: The incoming request.
        name: Which list.

    Returns:
        The list's empty state.
    """
    title, icon, text = COMING[name]
    return render(
        request,
        "masters/coming.html",
        {
            "title": title,
            "icon": icon,
            "heading": f"No {title.lower()} yet",
            "text": f"{text} Adding them comes soon.",
        },
    )


def assets(request: HttpRequest) -> HttpResponse:
    """List the Asset accounts by Kind.

    Args:
        request: The incoming request.

    Returns:
        The Assets list.
    """
    return render(request, "masters/assets.html", assets_list())


def asset(request: HttpRequest, pk: int) -> HttpResponse:
    """Show an Asset account beside the Assets list.

    Args:
        request: The incoming request.
        pk: The Account's id.

    Returns:
        The Account's detail.
    """
    account = get_object_or_404(Account, pk=pk, type=Account.Type.ASSET)
    return render(
        request,
        "masters/asset.html",
        {
            "account": account,
            "history": history.of(account),
            **assets_list(selected=account),
        },
    )


def new_asset(request: HttpRequest) -> HttpResponse:
    """Add an Asset account.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect to the new Account once added.
    """
    form = AssetAccountForm(
        request.POST or None, instance=Account(type=Account.Type.ASSET)
    )
    if form.is_valid():
        with transaction.atomic():
            account = form.save()
            record(account, history.Action.CREATED)
        messages.success(request, f"Added {account.name}.")
        return redirect("masters:asset", account.pk)
    return render(request, "masters/asset_form.html", {"form": form, **assets_list()})


def edit_asset(request: HttpRequest, pk: int) -> HttpResponse:
    """Change an Asset account.

    Args:
        request: The incoming request.
        pk: The Account's id.

    Returns:
        The form, or a redirect to the Account once changed.
    """
    account = get_object_or_404(Account, pk=pk, type=Account.Type.ASSET)
    # Taken before the form, which writes what's posted into the Account.
    before = snapshot(account)
    form = AssetAccountForm(request.POST or None, instance=account)
    if form.is_valid():
        with transaction.atomic():
            form.save()
            if changed := history.changes(before, snapshot(account)):
                record(account, history.Action.EDITED, changed)
        messages.success(request, "Saved.")
        return redirect("masters:asset", account.pk)
    return render(
        request,
        "masters/asset_form.html",
        {"form": form, "account": account, **assets_list(selected=account)},
    )


def snapshot(account: Account) -> dict[str, str]:
    """An Asset account's fields, written out as its History shows them.

    Args:
        account: The Account.

    Returns:
        Each field's name and value.
    """
    return {
        "Name": account.name,
        "Kind": account.get_kind_display(),
        "Opening balance": write(account.opening_balance),
        "Opened on": date_format(account.opened_on, "j M Y")
        if account.opened_on
        else "",
        "Notes": account.notes,
    }


def record(
    account: Account, action: history.Action, changes: list[list[str]] | None = None
) -> None:
    """Add an entry about an Account to History.

    Args:
        account: The Account, as it is after the change.
        action: What happened to it.
        changes: Each changed field as ``[name, old, new]``.
    """
    history.record(
        account,
        action,
        type_=account.get_type_display(),
        name=account.name,
        changes=changes,
    )


def assets_list(selected: Account | None = None) -> dict:
    """What the Assets list pane shows: Accounts grouped by Kind, with totals.

    Args:
        selected: The Account open beside the list, if any.

    Returns:
        The template context for the list pane.
    """
    accounts = Account.objects.filter(type=Account.Type.ASSET).order_by(Lower("name"))
    groups = []
    for kind in Account.Kind:
        of_kind = [a for a in accounts if a.kind == kind]
        if of_kind:
            groups.append((kind, of_kind, sum(a.balance for a in of_kind)))
    return {
        "groups": groups,
        "total": sum(a.balance for a in accounts),
        "selected": selected,
    }
