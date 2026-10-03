import pytest
from django.urls import URLResolver, get_resolver, reverse

from apps.core.testing import EMAIL, PASSWORD
from apps.signin.testing import authenticator_code, enter_code, sign_in

PUBLIC = {"sign_in", "manifest", "service_worker"}
# Open only while unclaimed; test_claim covers them.
CLAIM = {"claim", "claim_owner"}
# Reachable on the password alone; test_code_step and test_passkeys cover them.
SIGNING_IN = {
    "code_step",
    "choose_way",
    "set_up_authenticator",
    "passkey_register_begin",
    "passkey_register_complete",
}
# Public, but they take only a POST; test_passkeys covers them.
PASSKEY_SIGN_IN = {"passkey_sign_in_begin", "passkey_sign_in_complete"}


def kosha_routes(patterns=None):
    """Every named route outside the admin, which guards itself."""
    for pattern in get_resolver().url_patterns if patterns is None else patterns:
        if isinstance(pattern, URLResolver):
            if pattern.app_name != "admin":
                yield from kosha_routes(pattern.url_patterns)
        elif pattern.name:
            yield pattern.name


@pytest.mark.django_db
def test_every_page_but_the_public_ones_needs_sign_in(client):
    for name in set(kosha_routes()) - PUBLIC - CLAIM - PASSKEY_SIGN_IN - {"sign_out"}:
        url = reverse(name)

        response = client.get(url)

        assert response.status_code == 302, name
        assert response["Location"].startswith(reverse("sign_in")), name


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_every_page_but_signing_in_needs_the_code_step(client):
    sign_in(client)

    for name in (
        set(kosha_routes())
        - PUBLIC
        - CLAIM
        - SIGNING_IN
        - PASSKEY_SIGN_IN
        - {"sign_out"}
    ):
        url = reverse(name)

        response = client.get(url)

        assert response["Location"] == f"{reverse('code_step')}?next={url}", name


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_public_pages_open_without_sign_in(client):
    for name in PUBLIC:
        assert client.get(reverse(name)).status_code == 200, name


@pytest.mark.django_db
def test_sign_in_with_password_and_code_lands_home(client, authenticator):
    response = sign_in(client)

    assert response["Location"] == reverse("home")
    code_step = client.get(reverse("home"))["Location"]
    assert code_step.startswith(reverse("code_step"))
    response = client.post(
        code_step, {"code": authenticator_code(authenticator.bin_key)}
    )
    assert response["Location"] == reverse("home")
    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_sign_in_ignores_the_email_case(client):
    sign_in(client, email="Owner@Example.COM")

    assert client.get(reverse("home"))["Location"].startswith(reverse("code_step"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "not it"), ("someone@example.com", PASSWORD)],
)
def test_wrong_credentials_show_an_error(client, owner, email, password):
    response = sign_in(client, email=email, password=password)

    assert response.status_code == 200
    assert "That email and password don't match." in response.text
    assert client.get(reverse("home")).status_code == 302


@pytest.mark.django_db
def test_signed_in_visit_to_sign_in_goes_home(signed_in):
    response = signed_in.get(reverse("sign_in"))

    assert response["Location"] == reverse("home")


@pytest.mark.django_db
def test_sign_out(signed_in):
    response = signed_in.post(reverse("sign_out"))

    assert response["Location"] == reverse("sign_in")
    assert signed_in.get(reverse("home")).status_code == 302


@pytest.mark.django_db
def test_sign_out_after_the_sign_in_has_expired(client):
    response = client.post(reverse("sign_out"))

    assert response["Location"] == reverse("sign_in")


@pytest.mark.django_db
def test_sign_in_follows_next_within_kosha(client, owner):
    admin = reverse("admin:index")

    response = sign_in(client, next=admin)

    assert response["Location"] == admin


@pytest.mark.django_db
@pytest.mark.parametrize(
    "next_url", ["https://evil.example/", "//evil.example/", "http://testserver.evil/"]
)
def test_sign_in_ignores_next_outside_kosha(client, owner, next_url):
    response = sign_in(client, next=next_url)

    assert response["Location"] == reverse("home")


@pytest.mark.django_db
def test_sign_in_lasts_30_days_from_the_last_visit(client, authenticator, clock):
    sign_in(client)
    enter_code(client, authenticator_code(authenticator.bin_key))

    clock.advance(days=29)
    assert client.get(reverse("home")).status_code == 200
    clock.advance(days=29)
    assert client.get(reverse("home")).status_code == 200

    clock.advance(days=30, seconds=1)
    assert client.get(reverse("home")).status_code == 302


@pytest.mark.django_db
def test_admin_login_goes_through_kosha_sign_in_and_back(client, authenticator):
    admin = reverse("admin:index")

    response = client.get(admin, follow=True)

    sign_in_url = f"{reverse('sign_in')}?next={admin}"
    assert response.redirect_chain[-1][0] == sign_in_url
    assert sign_in(client, next=admin)["Location"] == admin
    code = authenticator_code(authenticator.bin_key)
    assert enter_code(client, code, admin)["Location"] == admin
    assert client.get(admin).status_code == 200


@pytest.mark.django_db
def test_admin_login_with_no_next_comes_back_to_the_admin(client):
    response = client.get(reverse("admin:login"))

    admin = reverse("admin:index")
    assert response["Location"] == f"{reverse('sign_in')}?next={admin}"
