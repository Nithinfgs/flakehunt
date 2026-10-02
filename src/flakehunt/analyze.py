"""Turn N runs of a suite into per-test flakiness statistics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .junit import FAIL, PASS, SKIP, Case

STABLE, FLAKY, BROKEN, SKIPPED = "stable", "flaky", "broken", "skipped"

_NORMALISERS = [
    (re.compile(r"0x[0-9a-fA-F]+"), "0xN"),
    (re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F-]{4,}-[0-9a-fA-F-]+"), "<uuid>"),
    (re.compile(r"(?:/tmp|/var/folders|/private/var)[^\s'\"]*"), "<tmp>"),
    (re.compile(r"\d+(?:\.\d+)?"), "N"),
]

# (pattern, label, advice). Heuristics on failure text: suggestions, not diagnoses.
HINTS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"address already in use|eaddrinuse|errno (?:98|48)", re.I),
        "port collision",
        "bind to port 0 instead of a fixed port",
    ),
    (
        re.compile(r"connection (?:refused|reset|aborted)|econn(?:refused|reset)", re.I),
        "network or service startup",
        "wait for readiness explicitly",
    ),
    (
        re.compile(r"time(?:d)? ?out|deadline|took too long", re.I),
        "timing",
        "poll instead of sleeping or tight deadlines",
    ),
    (
        re.compile(
            r"database is locked|deadlock|could not serialize|unique constraint|duplicate key", re.I
        ),
        "shared database state",
        "isolate with per-test transactions or schemas",
    ),
    (
        re.compile(r"no such file|fileexists|enoent|directory not empty|permission denied", re.I),
        "filesystem state",
        "use a per-test temp directory",
    ),
    (
        re.compile(r"event loop is closed|cancellederror|coroutine .* never awaited", re.I),
        "async lifecycle",
        "await or cancel tasks before teardown",
    ),
    (
        re.compile(r"\b(?:429|502|503|504)\b|rate limit|max retries|service unavailable", re.I),
        "external service",
        "stub the remote service",
    ),
    (
        re.compile(r"timezone|tzinfo|utcnow|strftime|midnight|\bdst\b", re.I),
        "wall-clock dependence",
        "freeze the clock",
    ),
    (
        re.compile(r"random|seed|shuffle", re.I),
        "randomness",
        "seed it and log the seed",
    ),
]


def fingerprint(message: str) -> str:
    out = message
    for pattern, repl in _NORMALISERS:
        out = pattern.sub(repl, out)
    return out[:160]


def hint_for(messages: list[str]) -> tuple[str, str] | None:
    blob = "\n".join(messages)
    for pattern, label, advice in HINTS:
        if pattern.search(blob):
            return label, advice
    return None


@dataclass
class TestStat:
    __test__ = False  # not a pytest class

    id: str
    outcomes: list[str]  # one entry per run: pass | fail | skip | "" (absent)
    messages: list[str] = field(default_factory=list)
    fingerprints: dict[str, int] = field(default_factory=dict)
    alone: str = ""  # "pass" | "fail" | "": result when re-run by itself (pytest only)

    @property
    def passes(self) -> int:
        return self.outcomes.count(PASS)

    @property
    def fails(self) -> int:
        return self.outcomes.count(FAIL)

    @property
    def executed(self) -> int:
        return self.passes + self.fails

    @property
    def rate(self) -> float:
        return self.fails / self.executed if self.executed else 0.0

    @property
    def status(self) -> str:
        if self.executed == 0:
            return SKIPPED
        if self.fails == 0:
            return STABLE
        if self.passes == 0:
            return BROKEN
        return FLAKY

    @property
    def hint(self) -> tuple[str, str] | None:
        return hint_for(self.messages) if self.status in (FLAKY, BROKEN) else None


def analyse(runs: list[list[Case]]) -> list[TestStat]:
    """Aggregate per-run case lists. ``runs[i]`` holds the cases from run ``i``."""
    ids: list[str] = []
    seen: set[str] = set()
    for cases in runs:
        for c in cases:
            if c.id not in seen:
                seen.add(c.id)
                ids.append(c.id)
    stats = {i: TestStat(i, []) for i in ids}
    for cases in runs:
        by_id = {c.id: c for c in cases}
        for i, st in stats.items():
            case = by_id.get(i)
            st.outcomes.append(case.outcome if case else "")
            if case and case.outcome == FAIL and case.message:
                st.messages.append(case.message)
                fp = fingerprint(case.message)
                st.fingerprints[fp] = st.fingerprints.get(fp, 0) + 1
    return list(stats.values())


def miss_probability(rate: float, runs: int) -> float:
    """Chance that a test failing with probability ``rate`` never fails in ``runs`` runs."""
    return (1.0 - rate) ** runs


__all__ = [
    "BROKEN",
    "FLAKY",
    "SKIP",
    "SKIPPED",
    "STABLE",
    "TestStat",
    "analyse",
    "fingerprint",
    "hint_for",
    "miss_probability",
]
