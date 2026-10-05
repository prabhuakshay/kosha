"""Categories: their list, each one's detail and form, and what can be done to them."""

from typing import TYPE_CHECKING

from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core import history
from apps.masters.forms import CategoryForm
from apps.masters.models import Category

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def category_list(request: HttpRequest) -> HttpResponse:
    """List the Categories.

    Args:
        request: The incoming request.

    Returns:
        The list.
    """
    return render(request, "masters/categories.html", list_pane())


def category_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Show a Category beside the list.

    Args:
        request: The incoming request.
        pk: The Category's id.

    Returns:
        The Category's detail.
    """
    category = get_object_or_404(Category, pk=pk)
    return render(
        request,
        "masters/category.html",
        {
            "category": category,
            "history": history.of(category),
            **list_pane(selected=category),
        },
    )


def new_category(request: HttpRequest) -> HttpResponse:
    """Add a Category.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect to the new Category once added.
    """
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            category = form.save()
            record(category, history.Action.CREATED)
        messages.success(request, f"Added {category.name}.")
        return redirect("masters:category", category.pk)
    return render(request, "masters/category_new.html", {"form": form, **list_pane()})


def edit_category(request: HttpRequest, pk: int) -> HttpResponse:
    """Change a Category.

    Args:
        request: The incoming request.
        pk: The Category's id.

    Returns:
        The form, or a redirect to the Category once changed.
    """
    category = get_object_or_404(Category, pk=pk)
    # Taken before the form, which writes what's posted into the Category.
    before = snapshot(category)
    form = CategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        with transaction.atomic():
            form.save()
            if changed := history.changes(before, snapshot(category)):
                record(category, history.Action.EDITED, changed)
        messages.success(request, "Saved.")
        return redirect("masters:category", category.pk)
    return render(
        request,
        "masters/category_edit.html",
        {
            "form": form,
            "category": category,
            "history": history.of(category),
            **list_pane(selected=category),
        },
    )


@require_POST
def close_category(request: HttpRequest, pk: int) -> HttpResponse:
    """Close a Category.

    Args:
        request: The incoming request.
        pk: The Category's id.

    Returns:
        A redirect to the Category.
    """
    category = get_object_or_404(Category, pk=pk)
    if not category.closed:
        with transaction.atomic():
            category.closed = True
            category.save(update_fields=["closed"])
            record(category, history.Action.CLOSED)
        messages.success(request, f"Closed {category.name}.")
    return redirect("masters:category", category.pk)


@require_POST
def reopen_category(request: HttpRequest, pk: int) -> HttpResponse:
    """Reopen a Closed Category.

    Args:
        request: The incoming request.
        pk: The Category's id.

    Returns:
        A redirect to the Category.
    """
    category = get_object_or_404(Category, pk=pk)
    if category.closed:
        with transaction.atomic():
            category.closed = False
            category.save(update_fields=["closed"])
            record(category, history.Action.REOPENED)
        messages.success(request, f"Reopened {category.name}.")
    return redirect("masters:category", category.pk)


@require_POST
def delete_category(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete a Category nothing refers to, keeping its History.

    Args:
        request: The incoming request.
        pk: The Category's id.

    Returns:
        A redirect to the list, or to the Category if it's in use.
    """
    category = get_object_or_404(Category, pk=pk)
    if category.in_use:
        messages.error(
            request,
            f"{category.name} can't be deleted while anything refers to it. "
            "Close it instead.",
        )
        return redirect("masters:category", category.pk)
    with transaction.atomic():
        record(category, history.Action.DELETED)
        category.delete()
    messages.success(request, f"Deleted {category.name}.")
    return redirect("masters:categories")


def snapshot(category: Category) -> dict[str, str]:
    """A Category's fields, written out as its History shows them.

    Args:
        category: The Category.

    Returns:
        Each field's name and value.
    """
    return {
        "Name": category.name,
        "Color": category.get_color_display(),
        "Icon": category.get_icon_display(),
    }


def record(
    category: Category,
    action: history.Action,
    changes: list[list[str]] | None = None,
) -> None:
    """Add an entry about a Category to History.

    Args:
        category: The Category, as it is after the change.
        action: What happened to it.
        changes: Each changed field as ``[name, old, new]``.
    """
    history.record(
        category, action, type_="Category", name=category.name, changes=changes
    )


def list_pane(selected: Category | None = None) -> dict:
    """What the list pane shows: the open Categories, then the Closed ones.

    Args:
        selected: The Category open beside the list, if any.

    Returns:
        The template context for the list pane.
    """
    categories = list(Category.objects.order_by(Lower("name")))
    return {
        "categories": [c for c in categories if not c.closed],
        "closed": [c for c in categories if c.closed],
        "selected": selected,
    }
