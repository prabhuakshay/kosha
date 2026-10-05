"""Settings' own list, shown beside every page in Settings: ``{% settings_list %}``."""

from django import template

from apps.core.money import base_currency
from apps.masters.models import Account, Category, Tag

register = template.Library()


def count(items: list[Account] | list[Category]) -> str:
    """Say how many open ones a list holds.

    Args:
        items: Its Accounts or Categories, Closed ones included.

    Returns:
        Such as ``3 open``, ``None open`` or ``None yet``.
    """
    if not items:
        return "None yet"
    return f"{sum(not i.closed for i in items) or 'None'} open"


@register.inclusion_tag("core/_settings_list.html", takes_context=True)
def settings_list(context: template.Context) -> dict:
    """List Settings, with what each holds or is set to.

    Args:
        context: The page's context.

    Returns:
        The list's context.
    """
    request = context["request"]
    return {
        "request": request,
        "user": context["user"],
        "accounts": count(list(Account.objects.all())),
        "categories": count(list(Category.objects.all())),
        "tags": Tag.objects.count() or "None yet",
        "base_currency": base_currency(),
        "theme": context["theme"],
    }
