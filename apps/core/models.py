"""Settings that belong to the install as a whole."""

from typing import Self

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


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


class HistoryEntry(models.Model):
    """A change to an Account, Category, Tag or Setting, kept forever.

    The subject's type and name are copied in, and its id kept without a
    foreign key, so the entry still reads correctly once the subject is gone.
    """

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        EDITED = "edited", "Edited"
        BASE_CURRENCY_CHANGED = "base_currency_changed", "Base currency changed"

    at = models.DateTimeField(default=timezone.now, db_index=True)
    action = models.CharField(max_length=32, choices=Action)
    subject_model = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    subject_id = models.PositiveBigIntegerField()
    subject_type = models.CharField(max_length=32)
    subject_name = models.CharField(max_length=100)
    # Written out as [name, old, new] text, so an entry still reads as it did
    # after a Kind is renamed or the Base currency changes.
    changes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-at", "-pk"]
        verbose_name_plural = "history entries"
        indexes = [models.Index(fields=["subject_model", "subject_id"])]

    def __str__(self) -> str:
        return f"{self.get_action_display()} {self.subject_name}"
