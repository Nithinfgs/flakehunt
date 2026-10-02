import pytest

from shop.pricing import discount, with_tax


@pytest.mark.parametrize("total,pct,expected", [(100, 10, 90), (50, 0, 50), (80, 25, 60),
                                                (20, 50, 10), (0, 30, 0), (200, 100, 0)])
def test_discount(total, pct, expected):
    assert discount(total, pct) == expected


@pytest.mark.parametrize("total", [10, 20, 30, 40, 50, 60, 70, 80])
def test_tax_is_twenty_percent(total):
    assert with_tax(total) == round(total * 1.2, 2)


def test_tax_custom_rate():
    assert with_tax(100, 0.1) == 110
