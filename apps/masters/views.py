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
from apps.masters.listings import LISTINGS
from apps.masters.models import KINDS, Account
from apps.masters.worth import worth

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from apps.masters.listings import Listing


def accounts(request: HttpRequest) -> HttpResponse:
    """List every Account, with what the open ones add up to beside them.

    Args:
        request: The incoming request.

    Returns:
        The list of Accounts.
    """
    return render(request, "masters/accounts.html", {"worth": worth(), **list_pane()})


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
            "listing": listing,
            "history": history.of(account),
            "cant_close": cant_close(account),
            **list_pane(selected=account),
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
        request,
        "masters/account_new.html",
        {"form": form, "listing": listing, "worth": worth(), **list_pane()},
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
        "masters/account_edit.html",
        {
            "form": form,
            "account": account,
            "listing": listing,
            "history": history.of(account),
            "cant_close": cant_close(account),
            **list_pane(selected=account),
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
    return redirect("masters:accounts")


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


def list_pane(selected: Account | None = None) -> dict:
    """What the list pane shows: each type's open Accounts, then the Closed ones.

    Open Accounts are grouped by Kind with totals, for the types that have
    Kinds.

    Args:
        selected: The Account open beside the list, if any.

    Returns:
        The template context for the list pane.
    """
    accounts = list(Account.objects.order_by(Lower("name")))
    sections = []
    for listing in LISTINGS.values():
        of_type = [a for a in accounts if a.type == listing.type and not a.closed]
        groups = []
        for kind in listing.kinds:
            of_kind = [a for a in of_type if a.kind == kind]
            if of_kind:
                groups.append((kind, of_kind, sum(a.balance for a in of_kind)))
        sections.append(
            {
                "listing": listing,
                "accounts": of_type,
                "groups": groups,
                "total": sum(a.balance for a in of_type),
            }
        )
    return {
        "sections": sections,
        "closed": [(a, LISTINGS[a.type]) for a in accounts if a.closed],
        "selected": selected,
    }
