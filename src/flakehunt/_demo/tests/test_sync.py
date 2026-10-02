from conftest import chance


def test_websocket_reconnects():
    # Simulates a service that is sometimes not ready yet (about 1 run in 3).
    if chance("ws", 0.34):
        raise ConnectionRefusedError("[Errno 61] Connection refused: ws://127.0.0.1:8731")


def test_cache_warms_before_deadline():
    # Simulates a deadline missed on slow machines (about 1 run in 5).
    if chance("cache", 0.2):
        raise TimeoutError("cache warm-up exceeded 0.250s deadline (took 0.412s)")


def test_sync_idempotent():
    assert sorted([3, 1, 2]) == [1, 2, 3]
