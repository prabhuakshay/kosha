"""Helpers for tests that Claim Kosha and sign in, as the Owner would."""

import re
import secrets
import time
from base64 import b32decode
from io import StringIO
from typing import TYPE_CHECKING

from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp_webauthn.models import WebAuthnCredential

from apps.core.testing import EMAIL, PASSWORD

if TYPE_CHECKING:
    from django.http import HttpResponse
    from django_otp.plugins.otp_totp.models import TOTPDevice

    from apps.users.models import User

DETAILS = {"name": "Asha Rao", "email": EMAIL, "password": PASSWORD}
CHROME_ON_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
SAFARI_ON_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
FIREFOX_ON_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
)


def browser_at(address: str, user_agent: str = CHROME_ON_MAC) -> Client:
    """A browser of its own, at an address.

    Args:
        address: Where it connects from.
        user_agent: What it says it is.

    Returns:
        A test client with no Session yet.
    """
    return Client(REMOTE_ADDR=address, HTTP_USER_AGENT=user_agent)


def printed_code() -> str:
    """Read the Setup code as the ``setup_code`` command prints it.

    Returns:
        The code, in groups of four.
    """
    out = StringIO()
    call_command("setup_code", stdout=out)
    return re.search(r"Setup code: (\d{4} \d{4} \d{4})", out.getvalue())[1]


def enter_setup_code(client: Client, code: str | None = None) -> HttpResponse:
    """Enter a Setup code at step 1 of Claim.

    Args:
        client: The test client.
        code: What to type; the printed Setup code if omitted.

    Returns:
        The response.
    """
    return client.post(reverse("claim"), {"code": code or printed_code()})


def claim(client: Client, **details: str) -> HttpResponse:
    """Claim Kosha up to choosing a Way to sign in.

    Args:
        client: The test client.
        **details: Owner details to use instead of the defaults.

    Returns:
        The response to the Owner details.
    """
    enter_setup_code(client)
    return client.post(reverse("claim_owner"), {**DETAILS, **details})


def authenticator_code(key: bytes, steps_ahead: int = 0) -> str:
    """Read the code an Authenticator app holding this key shows.

    Args:
        key: The Authenticator app's key.
        steps_ahead: How many 30-second steps from now; a code is used once, so
            a second check soon after needs the next.

    Returns:
        The 6-digit code.
    """
    totp = TOTP(key)
    totp.time = time.time() + steps_ahead * totp.step
    return f"{totp.token():06d}"


def shown_key(response: HttpResponse) -> str:
    """Read the key the Authenticator app setup shows for typing in.

    Args:
        response: The setup page.

    Returns:
        The key, in groups of four.
    """
    return re.search(r"data-authenticator-key>([A-Z2-7 ]+)<", response.text)[1]


def shown_codes(response: HttpResponse) -> list[str]:
    """Read the Recovery codes a page shows.

    Args:
        response: The page.

    Returns:
        Each code, in two groups of four.
    """
    return re.findall(r"data-recovery-code>([a-z2-7]{4} [a-z2-7]{4})<", response.text)


def set_up_authenticator(
    client: Client, code: str | None = None, route: str = "set_up_authenticator"
) -> HttpResponse:
    """Scan the setup's key into an Authenticator app and type its code.

    Args:
        client: The test client.
        code: What to type; the app's code if omitted.
        route: The setup's route name.

    Returns:
        The response to the code.
    """
    key = shown_key(client.get(reverse(route)))
    code = code or authenticator_code(b32decode(key.replace(" ", "")))
    return client.post(reverse(route), {"code": code})


def replace_authenticator(client: Client, code: str | None = None) -> HttpResponse:
    """Set up an Authenticator app from Security, replacing any there is.

    Args:
        client: The test client, confirmed.
        code: What to type; the new app's code if omitted.

    Returns:
        The response to the code.
    """
    client.post(reverse("start_authenticator"))
    return set_up_authenticator(client, code, "new_authenticator")


def sign_in(
    client: Client, email: str = EMAIL, password: str = PASSWORD, **extra: str
) -> HttpResponse:
    """Sign in with an email and password.

    Args:
        client: The test client.
        email: What to type as the email.
        password: What to type as the password.
        **extra: More form fields, such as ``next``.

    Returns:
        The response.
    """
    return client.post(
        reverse("sign_in"), {"username": email, "password": password, **extra}
    )


def enter_code(client: Client, code: str, next_url: str | None = None) -> HttpResponse:
    """Type a code at the code step.

    Args:
        client: The test client.
        code: An Authenticator app or Recovery code.
        next_url: Where the code step should go on to.

    Returns:
        The response.
    """
    url = reverse("code_step") + (f"?next={next_url}" if next_url else "")
    return client.post(url, {"code": code})


def sign_in_fully(
    client: Client, authenticator: TOTPDevice, steps_ahead: int = 0
) -> HttpResponse:
    """Sign in with the password and a code from the Authenticator app.

    Args:
        client: The test client.
        authenticator: The Owner's Authenticator app.
        steps_ahead: Which code to type; each is used once, so a later sign-in
            needs a later one.

    Returns:
        The response to the code.
    """
    sign_in(client)
    return enter_code(client, authenticator_code(authenticator.bin_key, steps_ahead))


def add_recovery_code(owner: User, code: str = "k7m2x9qa") -> str:
    """Give the Owner a Recovery code.

    Args:
        owner: Whose it is.
        code: The code.

    Returns:
        The code.
    """
    StaticDevice.objects.get_or_create(user=owner)[0].token_set.create(token=code)
    return code


def add_passkey(owner: User, name: str = "Passkey") -> WebAuthnCredential:
    """Save a Passkey as if the browser had just registered it.

    Args:
        owner: Whose it is.
        name: What it's called.

    Returns:
        The Passkey.
    """
    return WebAuthnCredential.objects.create(
        user=owner, name=name, credential_id=secrets.token_bytes(16)
    )


def post_json(client: Client, name: str, query: str = "") -> HttpResponse:
    """POST to a Passkey ceremony as ``passkey.js`` does.

    Args:
        client: The test client.
        name: The route's name.
        query: A query string to add, such as ``?next=/``.

    Returns:
        The response.
    """
    return client.post(reverse(name) + query, "{}", content_type="application/json")


def register_passkey(client: Client) -> HttpResponse:
    """Run the ceremony that adds a Passkey, its browser part stubbed.

    Args:
        client: The test client.

    Returns:
        The response to completing it.
    """
    post_json(client, "passkey_register_begin")
    return post_json(client, "passkey_register_complete")


def sign_in_with_passkey(client: Client, next_url: str | None = None) -> HttpResponse:
    """Run the ceremony that signs in with a Passkey, its browser part stubbed.

    Args:
        client: The test client.
        next_url: Where signing in should go on to.

    Returns:
        The response to completing it, whose JSON says where to go.
    """
    post_json(client, "passkey_sign_in_begin")
    query = f"?next={next_url}" if next_url else ""
    return post_json(client, "passkey_sign_in_complete", query)
