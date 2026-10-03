"""Masters: the Accounts, Categories and Tags everything else refers to."""

from typing import TYPE_CHECKING

from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.formats import date_format
from django.views.decorators.http import require_POST

from apps.core import history
from apps.core.money import write
from apps.masters.models import KINDS, Account, Category

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from apps.masters.listings import Listing

# Lists still to come: what belongs in each, for their empty states.
COMING = {
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
            "categories": summary(list(Category.objects.all())),
        },
    )


def summary(items: list[Account] | list[Category], *, total: bool = False) -> str:
    """Say how many open ones a list holds, and what they hold between them.

    Args:
        items: The list's Accounts or Categories, Closed ones included.
        total: Whether to add up their balances, for Accounts.

    Returns:
        Such as ``2 · ₹3,20,000.00``, ``None open`` or ``None yet``.
    """
    if not items:
        return "None yet"
    items = [i for i in items if not i.closed]
    if not items:
        return "None open"
    if total:
        return f"{len(items)} · {write(sum(i.balance for i in items))}"
    return str(len(items))


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


def account_list(request: HttpRequest, listing: Listing) -> HttpResponse:
    """List Accounts of one type, by Kind if it has them.

    Args:
        request: The incoming request.
        listing: Which list.

    Returns:
        The list.
    """
    return render(request, "masters/accounts.html", list_pane(listing))


def account_detail(request: HttpRequest, listing: Listing, pk: int) -> HttpResponse:
    """Show an Account beside its list.

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
            "cant_close": cant_close(account),
            **list_pane(listing, selected=account),
        },
    )


def new_account(request: HttpRequest, listing: Listing) -> HttpResponse:
    """Add an Account.

    Args:
        request: The incoming request.
        listing: Which list.

    Returns:
        The form, or a redirect to the new Account once added.
    """
    form = listing.form(request.POST or None, instance=Account(type=listing.type))
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
    """Change an Account, keeping it the same type.

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
    form = listing.form(request.POST or None, instance=account)
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


def cant_close(account: Account) -> str:
    """Why an Account can't be Closed, if it's open and can't be.

    Args:
        account: The Account.

    Returns:
        The reason, or nothing if it can be Closed.
    """
    if not account.closed and account.type in KINDS and account.balance:
        return (
            f"{account.name} can't be closed while its balance is "
            f"{write(account.balance)}. Only an account with a zero balance can be "
            "closed."
        )
    return ""


@require_POST
def close_account(request: HttpRequest, listing: Listing, pk: int) -> HttpResponse:
    """Close an Account, unless it still holds something.

    Args:
        request: The incoming request.
        listing: Which list.
        pk: The Account's id.

    Returns:
        A redirect to the Account.
    """
    account = get_object_or_404(Account, pk=pk, type=listing.type)
    if reason := cant_close(account):
        messages.error(request, reason)
    elif not account.closed:
        with transaction.atomic():
            account.closed = True
            account.save(update_fields=["closed"])
            record(account, history.Action.CLOSED)
        messages.success(request, f"Closed {account.name}.")
    return redirect(listing.detail, account.pk)


@require_POST
def reopen_account(request: HttpRequest, listing: Listing, pk: int) -> HttpResponse:
    """Reopen a Closed Account.

    Args:
        request: The incoming request.
        listing: Which list.
        pk: The Account's id.

    Returns:
        A redirect to the Account.
    """
    account = get_object_or_404(Account, pk=pk, type=listing.type)
    if account.closed:
        with transaction.atomic():
            account.closed = False
            account.save(update_fields=["closed"])
            record(account, history.Action.REOPENED)
        messages.success(request, f"Reopened {account.name}.")
    return redirect(listing.detail, account.pk)


@require_POST
def delete_account(request: HttpRequest, listing: Listing, pk: int) -> HttpResponse:
    """Delete an Account nothing refers to, keeping its History.

    Args:
        request: The incoming request.
        listing: Which list.
        pk: The Account's id.

    Returns:
        A redirect to the list, or to the Account if it's in use.
    """
    account = get_object_or_404(Account, pk=pk, type=listing.type)
    if account.in_use:
        messages.error(
            request,
            f"{account.name} can't be deleted while anything refers to it. "
            "Close it instead.",
        )
        return redirect(listing.detail, account.pk)
    with transaction.atomic():
        record(account, history.Action.DELETED)
        account.delete()
    messages.success(request, f"Deleted {account.name}.")
    return redirect(listing.list)


def snapshot(account: Account) -> dict[str, str]:
    """An Account's fields, written out as its History shows them.

    Args:
        account: The Account.

    Returns:
        Each field's name and value.
    """
    if account.type not in KINDS:
        return {"Name": account.name, "Notes": account.notes}
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
    """What a list pane shows: its open Accounts, then its Closed ones.

    Open Accounts are grouped by Kind with totals, if the list has Kinds.

    Args:
        listing: Which list.
        selected: The Account open beside the list, if any.

    Returns:
        The template context for the list pane.
    """
    accounts = list(Account.objects.filter(type=listing.type).order_by(Lower("name")))
    of_type = [a for a in accounts if not a.closed]
    groups = []
    for kind in listing.kinds:
        of_kind = [a for a in of_type if a.kind == kind]
        if of_kind:
            groups.append((kind, of_kind, sum(a.balance for a in of_kind)))
    return {
        "listing": listing,
        "accounts": of_type,
        "closed": [a for a in accounts if a.closed],
        "groups": groups,
        "total": sum(a.balance for a in of_type),
        "selected": selected,
    }
