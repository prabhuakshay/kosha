import json
import re

import pytest
from django.templatetags.static import static
from django.urls import reverse

from apps.core.testing import tags


@pytest.fixture(params=["sign_in", "home"])
def page_response(request, client):
    """A signed-out page and a signed-in one, both on the base layout."""
    if request.param == "home":
        client.force_login(request.getfixturevalue("owner"))
    return client.get(reverse(request.param))


@pytest.mark.django_db
def test_home_is_blank_and_signed_in(signed_in):
    response = signed_in.get(reverse("home"))

    assert response.status_code == 200
    assert tags(response, "h1")
    assert "Asha Rao" in response.text


@pytest.mark.django_db
def test_home_offers_sign_out(signed_in):
    response = signed_in.get(reverse("home"))

    assert tags(response, "form", method="post", action=reverse("sign_out"))


@pytest.mark.django_db
def test_every_script_carries_the_csp_nonce(page_response):
    response = page_response

    csp = response["Content-Security-Policy"]
    nonce = re.search(r"script-src [^;]*'nonce-([^']+)'", csp)[1]
    assert "unsafe-inline" not in csp
    scripts = tags(response, "script")
    assert scripts
    assert all(s.get("src") and s.get("nonce") == nonce for s in scripts)


@pytest.mark.django_db
def test_pages_make_kosha_installable(page_response):
    response = page_response

    assert tags(response, "link", rel="manifest", href=reverse("manifest"))
    assert tags(
        response,
        "link",
        rel="apple-touch-icon",
        href=static("icons/apple-touch-icon.png"),
    )
    themes = {
        m["media"]: m["content"] for m in tags(response, "meta", name="theme-color")
    }
    assert themes == {
        "(prefers-color-scheme: light)": "#f5f6f5",
        "(prefers-color-scheme: dark)": "#121513",
    }


@pytest.mark.django_db
def test_pages_register_the_service_worker(page_response):
    response = page_response

    assert tags(
        response, "script", **{"data-service-worker": reverse("service_worker")}
    )


@pytest.mark.django_db
def test_manifest(client):
    response = client.get(reverse("manifest"))

    assert response["Content-Type"] == "application/manifest+json"
    manifest = json.loads(response.content)
    assert manifest["name"] == "Kosha"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == reverse("home")
    assert manifest["theme_color"] == "#f5f6f5"
    assert manifest["background_color"] == "#f5f6f5"
    icons = {(i["sizes"], i.get("purpose", "any")): i["src"] for i in manifest["icons"]}
    assert icons == {
        ("192x192", "any"): static("icons/icon-192.png"),
        ("512x512", "any"): static("icons/icon-512.png"),
        ("512x512", "maskable"): static("icons/icon-maskable-512.png"),
    }


@pytest.mark.django_db
def test_service_worker_covers_the_app_and_caches_nothing(client):
    response = client.get(reverse("service_worker"))

    assert reverse("service_worker") == "/sw.js"
    assert response["Content-Type"].startswith("text/javascript")
    assert response["Cache-Control"] == "no-cache"
    body = response.text
    assert 'addEventListener("install"' in body
    assert 'addEventListener("fetch"' not in body
    assert "caches." not in body
