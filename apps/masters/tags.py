"""Tags: their list, each one's detail and form, and deleting them."""

from typing import TYPE_CHECKING

from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core import history
from apps.masters.forms import TagForm
from apps.masters.models import Tag

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def tag_list(request: HttpRequest) -> HttpResponse:
    """List the Tags.

    Args:
        request: The incoming request.

    Returns:
        The list.
    """
    return render(request, "masters/tags.html", list_pane())


def tag_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Show a Tag beside the list.

    Args:
        request: The incoming request.
        pk: The Tag's id.

    Returns:
        The Tag's detail.
    """
    tag = get_object_or_404(Tag, pk=pk)
    return render(
        request,
        "masters/tag.html",
        {"tag": tag, "history": history.of(tag), **list_pane(selected=tag)},
    )


def new_tag(request: HttpRequest) -> HttpResponse:
    """Add a Tag.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect to the new Tag once added.
    """
    form = TagForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            tag = form.save()
            record(tag, history.Action.CREATED)
        messages.success(request, f"Added {tag.name}.")
        return redirect("masters:tag", tag.pk)
    return render(request, "masters/tag_form.html", {"form": form, **list_pane()})


def edit_tag(request: HttpRequest, pk: int) -> HttpResponse:
    """Rename a Tag.

    Args:
        request: The incoming request.
        pk: The Tag's id.

    Returns:
        The form, or a redirect to the Tag once renamed.
    """
    tag = get_object_or_404(Tag, pk=pk)
    # Taken before the form, which writes what's posted into the Tag.
    before = tag.name
    form = TagForm(request.POST or None, instance=tag)
    if form.is_valid():
        with transaction.atomic():
            form.save()
            if before != tag.name:
                record(tag, history.Action.EDITED, [["Name", before, tag.name]])
        messages.success(request, "Saved.")
        return redirect("masters:tag", tag.pk)
    return render(
        request,
        "masters/tag_form.html",
        {"form": form, "tag": tag, **list_pane(selected=tag)},
    )


@require_POST
def delete_tag(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete a Tag nothing refers to, keeping its History.

    Args:
        request: The incoming request.
        pk: The Tag's id.

    Returns:
        A redirect to the list, or to the Tag if it's in use.
    """
    tag = get_object_or_404(Tag, pk=pk)
    if tag.in_use:
        messages.error(
            request, f"{tag.name} can't be deleted while anything refers to it."
        )
        return redirect("masters:tag", tag.pk)
    with transaction.atomic():
        record(tag, history.Action.DELETED)
        tag.delete()
    messages.success(request, f"Deleted {tag.name}.")
    return redirect("masters:tags")


def record(
    tag: Tag, action: history.Action, changes: list[list[str]] | None = None
) -> None:
    """Add an entry about a Tag to History.

    Args:
        tag: The Tag, as it is after the change.
        action: What happened to it.
        changes: Each changed field as ``[name, old, new]``.
    """
    history.record(tag, action, type_="Tag", name=tag.name, changes=changes)


def list_pane(selected: Tag | None = None) -> dict:
    """What the list pane shows: every Tag, alphabetically.

    Args:
        selected: The Tag open beside the list, if any.

    Returns:
        The template context for the list pane.
    """
    return {"tags": Tag.objects.order_by(Lower("name")), "selected": selected}
