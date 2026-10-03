"""Root URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.signin.views import admin_login

urlpatterns = [
    # Ahead of the admin's own login, so it has only one way in: Kosha's.
    path(f"{settings.ADMIN_URL}login/", admin_login),
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.signin.urls")),
    path("", include("apps.core.urls")),
]
