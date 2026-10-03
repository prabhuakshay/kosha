"""Settings that belong to the install as a whole."""

from typing import Self

from django.db import models


class Setting(models.Model):
    """The install's one row of Settings."""

    base_currency = models.CharField(max_length=3, default="INR")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(pk=1), name="one_setting_row")
        ]

    def __str__(self) -> str:
        return "Settings"

    @classmethod
    def load(cls) -> Self:
        """The one row, made with its defaults the first time it's asked for.

        Returns:
            The Settings.
        """
        return cls.objects.get_or_create(pk=1)[0]
