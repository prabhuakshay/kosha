"""The app shell: home, settings, and what makes Kosha installable."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse

from apps.core import appearance, history, time_zone
from apps.core.forms import BaseCurrencyForm, TimeZoneForm
from apps.core.models import Setting
from apps.masters.worth import worth

# Matches the light theme's page colour, so the splash screen doesn't flash.
THEME_COLOR = "#f3f3f1"


def home(request: HttpRequest) -> HttpResponse:
    """Show the home page, where signing in lands, with the Owner's Net worth.

    Args:
        request: The incoming request.

    Returns:
        The home page.
    """
    return render(request, "core/home.html", {"worth": worth()})


def settings(request: HttpRequest) -> HttpResponse:
    """List the settings, each leading to its own page.

    Args:
        request: The incoming request.

    Returns:
        The settings page.
    """
    return render(request, "core/settings.html")


def base_currency(request: HttpRequest) -> HttpResponse:
    """Choose the Base currency, which relabels every amount without converting it.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect back to it once changed.
    """
    setting = Setting.load()
    # Taken before the form, which writes what's posted into the Setting.
    before = setting.base_currency
    form = BaseCurrencyForm(request.POST or None, instance=setting)
    if form.is_valid():
        with transaction.atomic():
            form.save()
            changed = history.changes(
                {"Base currency": before}, {"Base currency": setting.base_currency}
            )
            if changed:
                history.record(
                    setting,
                    history.Action.BASE_CURRENCY_CHANGED,
                    type_="Setting",
                    name="Base currency",
                    changes=changed,
                )
        messages.success(request, f"Amounts are now in {form.instance.base_currency}.")
        return redirect("base_currency")
    return render(
        request,
        "core/base_currency.html",
        {"form": form, "sample": Decimal(320000)},
    )


def time_zone_page(request: HttpRequest) -> HttpResponse:
    """Choose the Time zone, which decides what today is and how times read.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect back to it once changed.
    """
    setting = Setting.load()
    before = time_zone.name()
    form = TimeZoneForm(
        request.POST or None, instance=setting, initial={"time_zone": before}
    )
    if form.is_valid():
        with transaction.atomic():
            form.save()
            changed = history.changes(
                {"Time zone": before}, {"Time zone": setting.time_zone}
            )
            if changed:
                history.record(
                    setting,
                    history.Action.TIME_ZONE_CHANGED,
                    type_="Setting",
                    name="Time zone",
                    changes=changed,
                )
        messages.success(request, f"Today is now worked out in {setting.time_zone}.")
        return redirect("time_zone")
    return render(request, "core/time_zone.html", {"form": form})


def history_page(request: HttpRequest) -> HttpResponse:
    """Every change to Masters and Settings, by day.

    Args:
        request: The incoming request.

    Returns:
        The History page.
    """
    return render(request, "core/history.html", {"days": history.by_day()})


def appearance_page(request: HttpRequest) -> HttpResponse:
    """Choose a light or dark theme for this browser, or Auto to follow the device.

    Kept in a cookie rather than a Setting, so each device can look its own way.

    Args:
        request: The incoming request.

    Returns:
        The choices, or a redirect back to them once one is made.
    """
    if request.method != "POST":
        return render(request, "core/appearance.html", {"themes": appearance.THEMES})
    response = redirect("appearance")
    theme = appearance.find(request.POST.get("theme"))
    if theme == appearance.AUTO:
        response.delete_cookie(appearance.COOKIE, samesite="Lax")
    elif theme:
        response.set_cookie(
            appearance.COOKIE,
            theme.value,
            max_age=appearance.LASTS,
            secure=request.is_secure(),
            httponly=True,
            samesite="Lax",
        )
    return response


# Browsers fetch the manifest without cookies, so it can't sit behind sign-in.
@login_not_required
def manifest(request: HttpRequest) -> JsonResponse:  # ruff: ignore[unused-function-argument]
    """Describe Kosha as an installable app.

    Args:
        request: The incoming request (unused).

    Returns:
        The web app manifest.
    """
    home_url = reverse("home")
    return JsonResponse(
        {
            "id": home_url,
            "name": "Kosha",
            "short_name": "Kosha",
            "start_url": home_url,
            "scope": home_url,
            "display": "standalone",
            "background_color": THEME_COLOR,
            "theme_color": THEME_COLOR,
            "icons": [
                {
                    "src": static("icons/icon-192.png"),
                    "sizes": "192x192",
                    "type": "image/png",
                },
                {
                    "src": static("icons/icon-512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                },
                {
                    "src": static("icons/icon-maskable-512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
        },
        content_type="application/manifest+json",
    )


# Served from the root rather than /static/ so its scope covers the whole app.
@login_not_required
def service_worker(request: HttpRequest) -> HttpResponse:
    """Serve the service worker.

    Args:
        request: The incoming request.

    Returns:
        The service worker script, revalidated on every check for updates.
    """
    response = render(request, "core/sw.js", content_type="text/javascript")
    response["Cache-Control"] = "no-cache"
    return response
