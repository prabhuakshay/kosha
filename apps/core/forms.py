"""Settings forms."""

from django import forms

from apps.core.models import Setting
from apps.core.money import currencies
from apps.core.time_zone import ZONES


class BaseCurrencyForm(forms.ModelForm):
    """Choose the Base currency from those in use today."""

    base_currency = forms.ChoiceField(choices=currencies)

    class Meta:
        model = Setting
        fields = ["base_currency"]


class TimeZoneForm(forms.ModelForm):
    """Choose the Time zone from those the server knows."""

    time_zone = forms.ChoiceField(choices=[(z, z) for z in ZONES])

    class Meta:
        model = Setting
        fields = ["time_zone"]
