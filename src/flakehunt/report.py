"""Render hunt and why results as terminal text, Markdown, or JSON."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from .analyze import BROKEN, FLAKY, TestStat, miss_probability
from .junit import FAIL, PASS
from .why import ALONE, ORDER, WhyResult

SCHEMA_VERSION = 1


class Style:
    def __init__(self, color: bool):
        self.color = color

    def _w(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def bold(self, t: str) -> str:
        return self._w("1", t)

    def dim(self, t: str) -> str:
        return self._w("2", t)

    def red(self, t: str) -> str:
        return self._w("31", t)

    def green(self, t: str) -> str:
        return self._w("32", t)

    def yellow(self, t: str) -> str:
        return self._w("33", t)

    def cyan(self, t: str) -> str:
        return self._w("36", t)


def want_color(stream: Any = None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


def strip(outcomes: list[str], style: Style) -> str:
    glyph = []
    for o in outcomes:
        if o == FAIL:
            glyph.append(style.red("✗"))
        elif o == PASS:
            glyph.append(style.dim("·"))
        else:
            glyph.append(" ")
    return "".join(glyph)


def _confidence_note(runs: int) -> str:
    rows = [
        f"{int(r * 100)}%: {int((1 - miss_probability(r, runs)) * 100)}%"
        for r in (0.5, 0.2, 0.1, 0.05)
    ]
    return f"Odds a flaky test is caught in {runs} runs, by its failure rate: " + ", ".join(rows)


def render_hunt(stats: list[TestStat], runs: int, command: str, style: Style) -> str:
    flaky = sorted((s for s in stats if s.status == FLAKY), key=lambda s: -s.rate)
    broken = [s for s in stats if s.status == BROKEN]
    total = len(stats)
    out = [
        f"{style.bold('flakehunt')} {style.dim('·')} {runs} runs {style.dim('·')} {total} tests "
        f"{style.dim('·')} {style.dim(command)}",
        "",
    ]
    if flaky:
        out.append(
            style.yellow(style.bold(f"FLAKY ({len(flaky)})"))
            + style.dim("  passed and failed on identical code")
        )
        for s in flaky:
            out.append(f"  {style.bold(s.id)}")
            out.append(
                f"    {style.red(f'{s.fails}/{s.executed} failed')} ({s.rate:.0%})  {strip(s.outcomes, style)}"
            )
            top = max(s.fingerprints.items(), key=lambda kv: kv[1]) if s.fingerprints else None
            if top:
                out.append(f"    {style.dim('fails with:')} {top[0]}")
                if len(s.fingerprints) > 1:
                    out.append(
                        f"    {style.dim(f'({len(s.fingerprints)} distinct failure messages)')}"
                    )
            h = s.hint
            if h:
                out.append(f"    {style.cyan('suspect:')} {h[0]} {style.dim('- ' + h[1])}")
        out.append("")
    else:
        out.append(style.green(f"No flaky tests observed in {runs} runs."))
        out.append("")
    if broken:
        out.append(
            style.red(style.bold(f"ALWAYS FAILING ({len(broken)})"))
            + style.dim("  broken, not flaky")
        )
        for s in broken:
            msg = s.messages[0] if s.messages else ""
            out.append(f"  {s.id}  {style.dim(msg)}")
            if s.alone == "pass":
                out.append(
                    f"    {style.yellow('passes when run alone')} {style.dim('-> order-dependent:')} "
                    f"flakehunt why {s.id}"
                )
            elif s.alone == "fail":
                out.append(f"    {style.dim('also fails alone: genuinely broken')}")
        out.append("")
    stable = sum(1 for s in stats if s.status == "stable")
    out.append(style.dim(f"{stable} stable, {len(flaky)} flaky, {len(broken)} always failing"))
    out.append(style.dim(_confidence_note(runs)))
    if flaky:
        out.append(
            style.dim("Passes alone but fails in the suite? ")
            + f"flakehunt why <node id> {style.dim('(pytest) finds the test polluting it.')}"
        )
    return "\n".join(out)


def render_why(res: WhyResult, style: Style) -> str:
    out = [f"{style.bold('flakehunt why')} {style.dim('·')} {res.target}", ""]
    out.append(f"  alone:               {res.alone_fails}/{res.alone_runs} failed")
    if res.verdict != ALONE:
        out.append(
            f"  after {res.prefix_size} earlier tests: {res.with_prefix_fails}/{res.with_prefix_runs} failed"
        )
    out.append("")
    if res.verdict == ALONE:
        out.append(style.yellow(style.bold("Verdict: intrinsically flaky.")))
        out.append("  It fails with no other test running, so the cause is inside the test or")
        out.append("  what it touches (time, randomness, network, ports, files).")
    elif res.verdict == ORDER:
        out.append(style.yellow(style.bold("Verdict: order-dependent.")))
        out.append("  It never failed alone, but fails once earlier tests have run.")
        out.append("")
        if res.polluters:
            word = "polluter" if len(res.polluters) == 1 else "polluters (jointly required)"
            out.append(style.bold(f"Minimal {word}:"))
            for p in res.polluters:
                out.append(f"  {style.red(p)}")
            out.append(
                style.dim(
                    f"  found with {res.ddmin_calls} probes"
                    + (" (budget hit: may not be minimal)" if res.exhausted else "")
                )
            )
            out.append("")
            out.append("Reproduce:")
            out.append("  " + res.reproduce.replace(" tests/", " \\\n    tests/"))
    else:
        out.append(style.green(style.bold("Verdict: could not reproduce.")))
        total = res.alone_runs + res.with_prefix_runs
        out.append(f"  No failure in {total} runs. A rare flake needs more runs: raise --runs.")
    if res.messages:
        out.append("")
        out.append(style.dim("failure: ") + res.messages[0])
        from .analyze import hint_for

        h = hint_for(res.messages)
        if h:
            out.append(f"{style.cyan('suspect:')} {h[0]} {style.dim('- ' + h[1])}")
    return "\n".join(out)


def to_json(stats: list[TestStat], runs: int, command: str) -> str:
    doc = {
        "schema": SCHEMA_VERSION,
        "command": command,
        "runs": runs,
        "tests": [
            {
                "id": s.id,
                "status": s.status,
                "passes": s.passes,
                "fails": s.fails,
                "failure_rate": round(s.rate, 4),
                "outcomes": s.outcomes,
                "failure_messages": s.fingerprints,
                "suspect": s.hint[0] if s.hint else None,
                "passes_alone": {"pass": True, "fail": False}.get(s.alone),
            }
            for s in stats
            if s.status in (FLAKY, BROKEN)
        ],
        "summary": {
            "tests": len(stats),
            "flaky": sum(1 for s in stats if s.status == FLAKY),
            "always_failing": sum(1 for s in stats if s.status == BROKEN),
        },
    }
    return json.dumps(doc, indent=2)


def to_markdown(stats: list[TestStat], runs: int, command: str) -> str:
    flaky = sorted((s for s in stats if s.status == FLAKY), key=lambda s: -s.rate)
    lines = [f"### flakehunt: {len(flaky)} flaky test(s) in {runs} runs", ""]
    if flaky:
        lines += ["| Test | Failed | Rate | Suspect | Failure |", "|---|---|---|---|---|"]
        for s in flaky:
            top = max(s.fingerprints, key=lambda k: s.fingerprints[k]) if s.fingerprints else ""
            sus = s.hint[0] if s.hint else ""
            lines.append(
                f"| `{s.id}` | {s.fails}/{s.executed} | {s.rate:.0%} | {sus} | `{top.replace('|', '/')}` |"
            )
    else:
        lines.append("No flaky tests observed.")
    lines += ["", f"<sub>`{command}` run {runs} times. " + _confidence_note(runs) + "</sub>"]
    return "\n".join(lines)
