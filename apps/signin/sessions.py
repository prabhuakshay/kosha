"""Every browser signed in as the Owner."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY

from apps.signin import client

if TYPE_CHECKING:
    from django.http import HttpRequest

    from apps.users.models import User

ADDRESS = "signin.address"
DEVICE = "signin.device"
SIGNED_IN_AT = "signin.signed_in_at"


@dataclass(frozen=True)
class OwnerSession:
    """One Session, as the Sessions screen shows it."""

    device: str
    address: str
    signed_in_at: datetime | None
    last_active: datetime
    current: bool
    password_only: bool


@receiver(user_logged_in)
def _stamp(request: HttpRequest, **_: object) -> None:
    request.session[ADDRESS] = client.address(request)
    request.session[DEVICE] = client.device(request)
    request.session[SIGNED_IN_AT] = timezone.now().timestamp()


def every_session(request: HttpRequest) -> list[OwnerSession]:
    """Every Session signed in as the Owner, this one first, then latest active.

    Args:
        request: The request whose Session is this one.

    Returns:
        The Sessions.
    """
    owner: User = request.user
    found = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        data = session.get_decoded()
        if data.get(SESSION_KEY) != str(owner.pk):
            continue
        stamped = data.get(SIGNED_IN_AT)
        current = session.session_key == request.session.session_key
        # Every request saves the session, so its expiry moves with each visit;
        # this one's is saved only after this request.
        last_active = (
            timezone.now()
            if current
            else session.expire_date - timedelta(seconds=settings.SESSION_COOKIE_AGE)
        )
        found.append(
            OwnerSession(
                device=data.get(DEVICE, "Unknown device"),
                address=data.get(ADDRESS, ""),
                signed_in_at=datetime.fromtimestamp(stamped, UTC) if stamped else None,
                last_active=last_active,
                current=current,
                password_only=DEVICE_ID_SESSION_KEY not in data,
            )
        )
    found.sort(key=lambda s: (s.current, s.last_active), reverse=True)
    return found


def sign_out_others(request: HttpRequest) -> None:
    """Sign out every Session but this one.

    Args:
        request: The request whose Session stays signed in.
    """
    # The Owner is the only login, so every other session is theirs.
    Session.objects.exclude(session_key=request.session.session_key).delete()
