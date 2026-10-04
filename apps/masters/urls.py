"""Masters: the Accounts, Categories and Tags everything else refers to."""

from django.urls import URLPattern, path

from apps.masters import categories, listings, tags, views


def account_routes(listing: listings.Listing) -> list[URLPattern]:
    """The routes of a list of Accounts of one type.

    Args:
        listing: Which list.

    Returns:
        The list, its form for a new Account, and each Account, its form and
        what can be done to it.
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
        *(
            path(f"{prefix}/<int:pk>/{action}/", view, kwargs, name=f"{action}_{route}")
            for action, view in [
                ("close", views.close_account),
                ("reopen", views.reopen_account),
                ("delete", views.delete_account),
            ]
        ),
    ]


app_name = "masters"
urlpatterns = [
    path("", views.masters, name="masters"),
    *account_routes(listings.ASSETS),
    *account_routes(listings.LIABILITIES),
    *account_routes(listings.INCOME),
    *account_routes(listings.EXPENSES),
    path("categories/", categories.category_list, name="categories"),
    path("categories/new/", categories.new_category, name="new_category"),
    path("categories/<int:pk>/", categories.category_detail, name="category"),
    path("categories/<int:pk>/edit/", categories.edit_category, name="edit_category"),
    *(
        path(f"categories/<int:pk>/{action}/", view, name=f"{action}_category")
        for action, view in [
            ("close", categories.close_category),
            ("reopen", categories.reopen_category),
            ("delete", categories.delete_category),
        ]
    ),
    path("tags/", tags.tag_list, name="tags"),
    path("tags/new/", tags.new_tag, name="new_tag"),
    path("tags/<int:pk>/", tags.tag_detail, name="tag"),
    path("tags/<int:pk>/edit/", tags.edit_tag, name="edit_tag"),
    path("tags/<int:pk>/delete/", tags.delete_tag, name="delete_tag"),
]
