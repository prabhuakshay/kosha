"""User models."""

from typing import ClassVar

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    """Manager for users identified by email instead of username."""

    use_in_migrations = True

    def get_by_natural_key(self, email: str) -> User:
        """Look up a user by email, so login is case-insensitive.

        Args:
            email: Email address to look up, in any case.

        Returns:
            The matching user.
        """
        return self.get(email=self.model.normalize_username(email))

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        """Create and save a user.

        Args:
            email: Email address, used to log in.
            password: Raw password. If omitted, the user gets an unusable password.
            **extra_fields: Other model field values.

        Returns:
            The created user.

        Raises:
            ValueError: If no email is given.
        """
        if not email:
            msg = "The email must be set."
            raise ValueError(msg)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=self.model.normalize_username(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        """Create and save a superuser.

        Args:
            email: Email address, used to log in.
            password: Raw password.
            **extra_fields: Other model field values.

        Returns:
            The created superuser.

        Raises:
            ValueError: If ``is_staff`` or ``is_superuser`` is not True.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields["is_superuser"] is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Project user, identified by email with a single name field."""

    email = models.EmailField("email address", unique=True)
    name = models.CharField(max_length=255)
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Unselect this instead of deleting accounts.",
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["name"]

    def __str__(self) -> str:
        return self.email

    @classmethod
    def normalize_username(cls, username: str) -> str:
        """Normalize an email for storage and lookup.

        Every creation and login path goes through this, which is what keeps
        the plain unique constraint on ``email`` effectively case-insensitive.

        Args:
            username: Email address as entered.

        Returns:
            The NFKC-normalized, lowercased email.
        """
        return super().normalize_username(username).strip().lower()

    @property
    def initials(self) -> str:
        """The first letters of the first two words of the name, for the avatar.

        Returns:
            Up to two capital letters.
        """
        return "".join(word[0] for word in self.name.split()[:2]).upper()

    def get_full_name(self) -> str:
        """Return the user's name.

        Returns:
            The user's name.
        """
        return self.name

    def get_short_name(self) -> str:
        """Return the user's name.

        Returns:
            The user's name.
        """
        return self.name
