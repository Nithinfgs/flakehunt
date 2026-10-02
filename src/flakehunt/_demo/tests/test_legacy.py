import pytest


def test_2019_tax_table():
    # Always fails: the table was removed. Broken, not flaky.
    raise AssertionError("tax table 2019 was removed in the v3 migration")


@pytest.mark.skip(reason="needs the old billing sandbox")
def test_sandbox_invoice():
    pass
