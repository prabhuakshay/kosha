"""The app shell."""

from django.urls import path

from apps.core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("settings/", views.settings, name="settings"),
    path("settings/base-currency/", views.base_currency, name="base_currency"),
    path("settings/history/", views.history_page, name="history"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
]
