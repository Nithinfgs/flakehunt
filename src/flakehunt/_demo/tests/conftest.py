"""Helpers that make the planted flakiness reproducible.

flakehunt exports FLAKEHUNT_RUN (1, 2, 3, ...) on every run. When it is set, the
"random" failures below are derived from it, so the demo gives the same answer every
time. Without it they use real randomness, like a genuinely flaky test would.
"""
import hashlib
import os
import random


def chance(name: str, probability: float) -> bool:
    run = os.environ.get("FLAKEHUNT_RUN")
    if run is None:
        return random.random() < probability
    digest = hashlib.sha256(f"{name}:{run}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2**32 < probability
