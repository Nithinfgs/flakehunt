"""Zeller's delta debugging (ddmin), specialised for finding test-order polluters."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


class BudgetExceeded(Exception):  # noqa: N818 - control-flow signal, not an error
    """Raised internally when the predicate-call budget runs out."""


def ddmin(
    items: Sequence[T],
    fails: Callable[[list[T]], bool],
    max_calls: int | None = None,
) -> tuple[list[T], int, bool]:
    """Shrink ``items`` to a 1-minimal subset for which ``fails`` is still true.

    ``fails(subset)`` must be true for the full list. Order of items is preserved.
    Returns ``(subset, predicate_calls, budget_exhausted)``. If the budget runs out the
    best subset found so far is returned (still failing, possibly not minimal).
    """
    cache: dict[tuple[int, ...], bool] = {}
    calls = 0
    index = {id(x): i for i, x in enumerate(items)}

    def check(subset: list[T]) -> bool:
        nonlocal calls
        key = tuple(index[id(x)] for x in subset)
        if key in cache:
            return cache[key]
        if max_calls is not None and calls >= max_calls:
            raise BudgetExceeded
        calls += 1
        result = fails(subset)
        cache[key] = result
        return result

    current = list(items)
    n = 2
    try:
        while len(current) >= 2:
            size = -(-len(current) // n)  # ceil division
            chunks = [current[i : i + size] for i in range(0, len(current), size)]
            reduced = False
            for chunk in chunks:
                if check(chunk):
                    current, n, reduced = chunk, 2, True
                    break
            if not reduced:
                for i in range(len(chunks)):
                    complement = [x for j, c in enumerate(chunks) if j != i for x in c]
                    if complement and check(complement):
                        current, n, reduced = complement, max(n - 1, 2), True
                        break
            if not reduced:
                if n >= len(current):
                    break
                n = min(len(current), n * 2)
        return current, calls, False
    except BudgetExceeded:
        return current, calls, True
