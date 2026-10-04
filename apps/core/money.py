"""The Base currency, and the one way amounts in it are written."""

from functools import cache
from operator import itemgetter
from typing import TYPE_CHECKING

from babel import Locale
from babel.localedata import locale_identifiers
from babel.numbers import (
    format_currency,
    get_currency_precision,
    get_territory_currencies,
)

from apps.core.models import Setting

if TYPE_CHECKING:
    from decimal import Decimal

ENGLISH = Locale("en")


@cache
def currencies() -> list[tuple[str, str]]:
    """Every currency in use somewhere today, by English name.

    Returns:
        Each currency's code and name.
    """
    codes = {c for t in ENGLISH.territories for c in get_territory_currencies(t)}
    return sorted(((c, ENGLISH.currencies[c]) for c in codes), key=itemgetter(1))


def base_currency() -> str:
    """The Base currency.

    Returns:
        Its code, such as ``INR``.
    """
    return Setting.load().base_currency


def decimal_places() -> int:
    """How many decimal places an amount in the Base currency may have.

    Returns:
        The count, such as 2 for INR and 0 for JPY.
    """
    return get_currency_precision(base_currency())


def write(amount: Decimal) -> str:
    """Write an amount the way the Base currency writes it.

    Args:
        amount: The amount.

    Returns:
        The amount with its symbol, grouping and decimal places, INR in lakhs.
    """
    currency = base_currency()
    return format_currency(amount, currency, locale=writing_locale(currency))


@cache
def writing_locale(currency: str) -> str:
    """The locale that writes a currency's amounts the way its country does.

    A currency code starts with its country's code, so English as spoken
    there gives that country's grouping while keeping symbols in English.
    Currencies with no such locale, such as EUR or JPY, are written in
    plain English.

    Args:
        currency: Its code, such as ``CHF``.

    Returns:
        A locale, such as ``en_CH``.
    """
    country = f"en_{currency[:2]}"
    return country if country in locale_identifiers() else "en"
