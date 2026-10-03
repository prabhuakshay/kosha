import importlib

import environ
import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django_otp_webauthn.models import WebAuthnCredential

from apps.core.testing import tags
from apps.signin.testing import (
    add_passkey,
    claim,
    post_json,
    register_passkey,
    sign_in,
    sign_in_with_passkey,
)
from config import settings as settings_module

pytestmark = pytest.mark.usefixtures("browser")


@pytest.fixture
def passkey(owner):
    return add_passkey(owner)


def passkey_button(response, action):
    return tags(response, "button", **{"data-passkey": action})


@pytest.mark.django_db
def test_claim_offers_a_passkey_going_on_to_recovery_codes(client):
    claim(client)

    response = client.get(reverse("choose_way"))

    [button] = passkey_button(response, "register")
    assert button["data-next"] == reverse("recovery_codes")


@pytest.mark.django_db
def test_claim_with_a_passkey(client):
    claim(client)

    begin = post_json(client, "passkey_register_begin")
    assert "challenge" in begin.json()
    assert begin.json()["rp"] == {"id": settings.OTP_WEBAUTHN_RP_ID, "name": "Kosha"}
    assert post_json(client, "passkey_register_complete").status_code == 200

    assert WebAuthnCredential.objects.count() == 1
    assert client.get(reverse("recovery_codes")).status_code == 200
    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_password_alone_cannot_add_a_passkey(client):
    sign_in(client)

    assert register_passkey(client).status_code == 403
    assert not WebAuthnCredential.objects.exists()


@pytest.mark.django_db
def test_a_passkey_cannot_be_added_once_there_is_a_way_to_sign_in(signed_in):
    assert register_passkey(signed_in).status_code == 403
    assert not WebAuthnCredential.objects.exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("passkey")
def test_sign_in_offers_a_passkey(client):
    response = client.get(reverse("sign_in"))

    [button] = passkey_button(response, "sign-in")
    assert "Sign in with a passkey" in response.text
    assert button["data-complete"].startswith(reverse("passkey_sign_in_complete"))


@pytest.mark.django_db
@pytest.mark.usefixtures("passkey")
def test_a_passkey_alone_signs_in_fully_verified(client):
    admin = reverse("admin:index")

    response = sign_in_with_passkey(client, admin)

    assert response.json()["redirect_url"] == admin
    assert client.get(admin).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("passkey")
def test_a_passkey_sign_in_ignores_next_outside_kosha(client):
    response = sign_in_with_passkey(client, "https://evil.example.com/")

    assert response.json()["redirect_url"] == reverse("home")


@pytest.mark.django_db
@pytest.mark.usefixtures("passkey")
def test_a_passkey_is_a_way_to_sign_in(client):
    sign_in(client)

    home = reverse("home")
    assert client.get(home)["Location"] == f"{reverse('code_step')}?next={home}"


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator", "passkey")
def test_code_step_offers_the_owners_passkey(client):
    sign_in(client)

    response = client.get(reverse("code_step"))

    assert passkey_button(response, "sign-in")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_code_step_offers_no_passkey_to_an_owner_without_one(client):
    sign_in(client)

    response = client.get(reverse("code_step"))

    assert not passkey_button(response, "sign-in")


@pytest.mark.django_db
@pytest.mark.usefixtures("passkey")
def test_code_step_without_an_authenticator_app_asks_for_a_recovery_code(client):
    sign_in(client)

    response = client.get(reverse("code_step"))

    assert "Use a passkey, or a recovery code." in response.text
    assert "Code from your authenticator app" not in response.text


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator", "passkey")
def test_a_passkey_at_the_code_step_finishes_signing_in(client):
    sign_in(client)

    response = sign_in_with_passkey(client)

    assert response.json()["redirect_url"] == reverse("home")
    assert client.get(reverse("home")).status_code == 200


@pytest.fixture
def load_settings(monkeypatch):
    """Load the settings module afresh with the variables given, ignoring .env."""
    monkeypatch.setattr(environ.Env, "read_env", lambda *args, **kwargs: None)
    for name in ("WEBAUTHN_ORIGINS", "WEBAUTHN_RP_ID", "CSRF_TRUSTED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/kosha")

    def load(**env):
        for name, value in {"DEBUG": "true", **env}.items():
            monkeypatch.setenv(name, value)
        return importlib.reload(settings_module)

    yield load
    monkeypatch.undo()
    importlib.reload(settings_module)


def test_passkey_origins_come_from_the_environment(load_settings):
    loaded = load_settings(
        WEBAUTHN_ORIGINS="https://kosha.example.com:8443,https://example.com",
        CSRF_TRUSTED_ORIGINS="https://other.example.com",
    )

    assert loaded.OTP_WEBAUTHN_ALLOWED_ORIGINS == [
        "https://kosha.example.com:8443",
        "https://example.com",
    ]
    assert loaded.OTP_WEBAUTHN_RP_ID == "kosha.example.com"
    assert loaded.OTP_WEBAUTHN_RP_NAME == "Kosha"


def test_passkey_origins_default_to_the_https_csrf_trusted_origins(load_settings):
    loaded = load_settings(
        DEBUG="false",
        CSRF_TRUSTED_ORIGINS=(
            "http://kosha.lan,https://*.example.com,https://kosha.example.com"
        ),
    )

    assert loaded.OTP_WEBAUTHN_ALLOWED_ORIGINS == ["https://kosha.example.com"]
    assert loaded.OTP_WEBAUTHN_RP_ID == "kosha.example.com"


def test_passkey_origins_default_to_localhost_in_development(load_settings):
    loaded = load_settings()

    assert loaded.OTP_WEBAUTHN_ALLOWED_ORIGINS == ["http://localhost:8000"]
    assert loaded.OTP_WEBAUTHN_RP_ID == "localhost"


def test_passkey_origins_are_required_in_production(load_settings):
    with pytest.raises(ImproperlyConfigured, match="WEBAUTHN_ORIGINS"):
        load_settings(DEBUG="false", CSRF_TRUSTED_ORIGINS="http://kosha.lan")


def test_relying_party_id_may_be_set_apart_from_the_origins(load_settings):
    loaded = load_settings(
        WEBAUTHN_ORIGINS="https://kosha.example.com", WEBAUTHN_RP_ID="example.com"
    )

    assert loaded.OTP_WEBAUTHN_RP_ID == "example.com"
