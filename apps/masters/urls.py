"""Masters: the Accounts, Categories and Tags everything else refers to."""

from django.urls import path

from apps.masters import views

app_name = "masters"
urlpatterns = [
    path("", views.masters, name="masters"),
    path("assets/", views.assets, name="assets"),
    path("assets/new/", views.new_asset, name="new_asset"),
    path("assets/<int:pk>/", views.asset, name="asset"),
    path("assets/<int:pk>/edit/", views.edit_asset, name="edit_asset"),
    *(
        path(f"{name}/", views.coming, {"name": name}, name=name)
        for name in views.COMING
    ),
]
