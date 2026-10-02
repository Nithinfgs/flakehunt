import pytest

from shop import settings
from shop.pricing import subtotal


@pytest.mark.parametrize("prices,expected", [([1, 2], 3), ([0.1, 0.2], 0.3), ([], 0), ([5], 5)])
def test_subtotal(prices, expected):
    assert subtotal(prices) == expected


def test_slow_network_profile():
    # Bug: tightens the global timeout for this test and never restores it.
    settings.TIMEOUT_SECONDS = 1
    assert settings.TIMEOUT_SECONDS == 1


def test_empty_cart_has_no_total():
    assert subtotal([]) == 0
