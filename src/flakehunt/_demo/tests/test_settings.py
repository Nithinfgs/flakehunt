from shop import settings


def test_default_timeout_is_30s():
    # Passes alone. Fails if an earlier test left TIMEOUT_SECONDS modified.
    assert settings.TIMEOUT_SECONDS == 30


def test_timeout_is_positive():
    assert settings.TIMEOUT_SECONDS > 0
