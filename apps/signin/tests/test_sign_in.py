import pytest
from django.urls import URLResolver, get_resolver, reverse

from apps.core.testing import EMAIL, PASSWORD

PUBLIC = {"sign_in", "manifest", "service_worker"}


def sign_in(client, email=EMAIL, password=PASSWORD, **extra):
    return client.post(
        reverse("sign_in"), {"username": email, "password": password, **extra}
    )


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
    for name in set(kosha_routes()) - PUBLIC - {"sign_out"}:
        url = reverse(name)

        response = client.get(url)

        assert response.status_code == 302, name
        assert response["Location"].startswith(reverse("sign_in")), name


@pytest.mark.django_db
def test_public_pages_open_without_sign_in(client):
    for name in PUBLIC:
        assert client.get(reverse(name)).status_code == 200, name


@pytest.mark.django_db
def test_sign_in_with_email_and_password_lands_home(client, owner):
    response = sign_in(client)

    assert response["Location"] == reverse("home")
    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
def test_sign_in_ignores_the_email_case(client, owner):
    sign_in(client, email="Owner@Example.COM")

    assert client.get(reverse("home")).status_code == 200


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
def test_sign_in_lasts_30_days_from_the_last_visit(client, owner, clock):
    sign_in(client)

    clock.advance(days=29)
    assert client.get(reverse("home")).status_code == 200
    clock.advance(days=29)
    assert client.get(reverse("home")).status_code == 200

    clock.advance(days=30, seconds=1)
    assert client.get(reverse("home")).status_code == 302


@pytest.mark.django_db
def test_admin_login_goes_through_kosha_sign_in_and_back(client, owner):
    admin = reverse("admin:index")

    response = client.get(admin, follow=True)

    sign_in_url = f"{reverse('sign_in')}?next={admin}"
    assert response.redirect_chain[-1][0] == sign_in_url
    assert sign_in(client, next=admin)["Location"] == admin
    assert client.get(admin).status_code == 200


@pytest.mark.django_db
def test_admin_login_with_no_next_comes_back_to_the_admin(client):
    response = client.get(reverse("admin:login"))

    admin = reverse("admin:index")
    assert response["Location"] == f"{reverse('sign_in')}?next={admin}"
