import pytest
from django.utils.timezone import localdate

from apps.masters.models import Account


@pytest.fixture
def hdfc():
    return Account.objects.create(
        type=Account.Type.ASSET,
        kind="bank",
        name="HDFC",
        opening_balance="320000",
        opened_on=localdate(),
    )
