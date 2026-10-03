"""The app shell: home, settings, and what makes Kosha installable."""

from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse

# Matches the light theme's page colour, so the splash screen doesn't flash.
THEME_COLOR = "#f5f6f5"


def home(request: HttpRequest) -> HttpResponse:
    """Show the home page, where signing in lands.

    Args:
        request: The incoming request.

    Returns:
        The home page.
    """
    return render(request, "core/home.html")


def settings(request: HttpRequest) -> HttpResponse:
    """List the settings, each leading to its own page.

    Args:
        request: The incoming request.

    Returns:
        The settings page.
    """
    return render(request, "core/settings.html")


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
