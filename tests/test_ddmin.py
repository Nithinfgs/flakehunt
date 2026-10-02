import random

from flakehunt.ddmin import ddmin


def test_finds_single_culprit():
    items = [f"t{i}" for i in range(40)]
    result, calls, exhausted = ddmin(items, lambda s: "t17" in s)
    assert result == ["t17"]
    assert not exhausted
    assert calls < 40


def test_finds_pair_that_must_co_occur():
    items = [f"t{i}" for i in range(30)]
    result, _, _ = ddmin(items, lambda s: "t3" in s and "t22" in s)
    assert result == ["t3", "t22"]


def test_preserves_order():
    items = list("abcdefgh")
    result, _, _ = ddmin(items, lambda s: "h" in s and "b" in s)
    assert result == ["b", "h"]


def test_budget_returns_best_so_far_still_failing():
    items = [f"t{i}" for i in range(64)]

    def culprit(s):
        return "t40" in s

    result, calls, exhausted = ddmin(items, culprit, max_calls=3)
    assert exhausted and calls == 3
    assert culprit(result)
    assert len(result) < len(items)


def test_single_item_is_returned_untouched():
    assert ddmin(["only"], lambda s: True)[0] == ["only"]


def test_random_culprit_sets_are_one_minimal():
    rng = random.Random(7)
    for _ in range(25):
        items = list(range(rng.randint(2, 50)))
        culprits = set(rng.sample(items, rng.randint(1, min(3, len(items)))))
        result, _, _ = ddmin(items, lambda s, c=culprits: c <= set(s))
        assert set(result) == culprits
