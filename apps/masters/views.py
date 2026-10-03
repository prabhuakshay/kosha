"""Masters: the Accounts, Categories and Tags everything else refers to."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.formats import date_format

from apps.core import history
from apps.core.money import write
from apps.masters.forms import AccountForm
from apps.masters.models import KINDS, Account

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

# Lists still to come: what belongs in each, for their empty states.
COMING = {
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


@dataclass(frozen=True)
class Listing:
    """A list of Asset accounts or Liabilities: its routes and what it says."""

    type: Account.Type
    plural: str
    title: str
    noun: str
    icon: str
    about: str
    lede: str
    total: str
    opening_note: str

    @property
    def list(self) -> str:
        """The list's route name."""
        return f"masters:{self.plural}"

    @property
    def detail(self) -> str:
        """The route name of an Account's detail."""
        return f"masters:{self.type}"

    @property
    def new(self) -> str:
        """The route name of the form adding an Account."""
        return f"masters:new_{self.type}"

    @property
    def edit(self) -> str:
        """The route name of the form account an Account."""
        return f"masters:edit_{self.type}"


ASSETS = Listing(
    type=Account.Type.ASSET,
    plural="assets",
    title="Assets",
    noun="asset account",
    icon="wallet",
    about="Money you have: bank accounts, deposits, cash and investments, money "
    "you've lent, and things you own such as a house or gold.",
    lede="Money you have, or something you own.",
    total="Total",
    opening_note="What it held when you started tracking it. Use a minus sign "
    "only if it was overdrawn.",
)
LIABILITIES = Listing(
    type=Account.Type.LIABILITY,
    plural="liabilities",
    title="Liabilities",
    noun="liability",
    icon="scale",
    about="Money you owe: credit cards, loans, a mortgage and debts to people.",
    lede="Money you owe, even if you can spend from it, such as a credit card.",
    total="Total owed",
    opening_note="What you owed when you started tracking it. Use a minus sign "
    "only if you were in credit.",
)


def account_list(request: HttpRequest, listing: Listing) -> HttpResponse:
    """List the Asset accounts or Liabilities by Kind.

    Args:
        request: The incoming request.
        listing: Which list.

    Returns:
        The list.
    """
    return render(request, "masters/accounts.html", list_pane(listing))


def account_detail(request: HttpRequest, listing: Listing, pk: int) -> HttpResponse:
    """Show an Asset account or Liability beside its list.

    Args:
        request: The incoming request.
        listing: Which list.
        pk: The Account's id.

    Returns:
        The Account's detail.
    """
    account = get_object_or_404(Account, pk=pk, type=listing.type)
    return render(
        request,
        "masters/account.html",
        {
            "account": account,
            "history": history.of(account),
            **list_pane(listing, selected=account),
        },
    )


def new_account(request: HttpRequest, listing: Listing) -> HttpResponse:
    """Add an Asset account or Liability.

    Args:
        request: The incoming request.
        listing: Which list.

    Returns:
        The form, or a redirect to the new Account once added.
    """
    form = AccountForm(request.POST or None, instance=Account(type=listing.type))
    if form.is_valid():
        with transaction.atomic():
            account = form.save()
            record(account, history.Action.CREATED)
        messages.success(request, f"Added {account.name}.")
        return redirect(listing.detail, account.pk)
    return render(
        request, "masters/account_form.html", {"form": form, **list_pane(listing)}
    )


def edit_account(request: HttpRequest, listing: Listing, pk: int) -> HttpResponse:
    """Change an Asset account or Liability, keeping it the same type.

    Args:
        request: The incoming request.
        listing: Which list.
        pk: The Account's id.

    Returns:
        The form, or a redirect to the Account once changed.
    """
    account = get_object_or_404(Account, pk=pk, type=listing.type)
    # Taken before the form, which writes what's posted into the Account.
    before = snapshot(account)
    form = AccountForm(request.POST or None, instance=account)
    if form.is_valid():
        with transaction.atomic():
            form.save()
            if changed := history.changes(before, snapshot(account)):
                record(account, history.Action.EDITED, changed)
        messages.success(request, "Saved.")
        return redirect(listing.detail, account.pk)
    return render(
        request,
        "masters/account_form.html",
        {
            "form": form,
            "account": account,
            **list_pane(listing, selected=account),
        },
    )


def snapshot(account: Account) -> dict[str, str]:
    """An Account's fields, written out as its History shows them.

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


def list_pane(listing: Listing, selected: Account | None = None) -> dict:
    """What a list pane shows: its Accounts grouped by Kind, with totals.

    Args:
        listing: Which list.
        selected: The Account open beside the list, if any.

    Returns:
        The template context for the list pane.
    """
    of_type = Account.objects.filter(type=listing.type).order_by(Lower("name"))
    groups = []
    for kind in KINDS[listing.type]:
        of_kind = [a for a in of_type if a.kind == kind]
        if of_kind:
            groups.append((kind, of_kind, sum(a.balance for a in of_kind)))
    return {
        "listing": listing,
        "groups": groups,
        "total": sum(a.balance for a in of_type),
        "selected": selected,
    }
