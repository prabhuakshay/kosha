"""Settings forms."""

from django import forms

from apps.core.models import Setting
from apps.core.money import currencies


class BaseCurrencyForm(forms.ModelForm):
    """Choose the Base currency from those in use today."""

    base_currency = forms.ChoiceField(choices=currencies)

    class Meta:
        model = Setting
        fields = ["base_currency"]
