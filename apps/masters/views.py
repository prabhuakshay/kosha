"""Masters: the Accounts, Categories and Tags everything else refers to."""

from typing import TYPE_CHECKING

from django.contrib import messages
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render

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
        {"account": account, **assets_list(selected=account)},
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
        account = form.save()
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
    form = AssetAccountForm(request.POST or None, instance=account)
    if form.is_valid():
        form.save()
        messages.success(request, "Saved.")
        return redirect("masters:asset", account.pk)
    return render(
        request,
        "masters/asset_form.html",
        {"form": form, "account": account, **assets_list(selected=account)},
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
