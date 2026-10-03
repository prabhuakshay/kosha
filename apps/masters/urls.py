"""Masters: the Accounts, Categories and Tags everything else refers to."""

from django.urls import URLPattern, path

from apps.masters import views


def account_routes(listing: views.Listing) -> list[URLPattern]:
    """The routes of a list of Accounts of one type.

    Args:
        listing: Which list.

    Returns:
        The list, its form for a new Account, and each Account and its form.
    """
    prefix, route, kwargs = listing.plural, listing.route, {"listing": listing}
    return [
        path(f"{prefix}/", views.account_list, kwargs, name=prefix),
        path(f"{prefix}/new/", views.new_account, kwargs, name=f"new_{route}"),
        path(f"{prefix}/<int:pk>/", views.account_detail, kwargs, name=route),
        path(
            f"{prefix}/<int:pk>/edit/",
            views.edit_account,
            kwargs,
            name=f"edit_{route}",
        ),
    ]


app_name = "masters"
urlpatterns = [
    path("", views.masters, name="masters"),
    *account_routes(views.ASSETS),
    *account_routes(views.LIABILITIES),
    *account_routes(views.INCOME),
    *account_routes(views.EXPENSES),
    *(
        path(f"{name}/", views.coming, {"name": name}, name=name)
        for name in views.COMING
    ),
]
