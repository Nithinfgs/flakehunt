"""`flakehunt why`: explain one failing test, and find the test that poisons it (pytest)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .analyze import hint_for
from .ddmin import ddmin
from .junit import FAIL, Case, parse_junit
from .runner import HuntError

# Flags that change collection output or stop the run early; we control these ourselves.
_NOISY = {"--quiet", "--verbose", "--exitfirst"}

ALONE, ORDER, UNREPRODUCED = "intrinsic", "order-dependent", "unreproduced"


@dataclass
class WhyResult:
    target: str
    verdict: str
    alone_fails: int
    alone_runs: int
    with_prefix_fails: int
    with_prefix_runs: int
    prefix_size: int
    polluters: list[str] = field(default_factory=list)
    ddmin_calls: int = 0
    exhausted: bool = False
    messages: list[str] = field(default_factory=list)
    reproduce: str = ""


def nodeid_to_junit(nodeid: str) -> tuple[str, str]:
    """``tests/test_a.py::Cls::test_x[p]`` -> (``tests.test_a.Cls``, ``test_x[p]``)."""
    path, *rest = nodeid.split("::")
    module = path[:-3] if path.endswith(".py") else path
    module = module.replace(os.sep, ".").replace("/", ".")
    if not rest:
        raise HuntError(f"not a pytest node id (expected path::name): {nodeid}")
    return ".".join([module, *rest[:-1]]), rest[-1]


def display_command(command: list[str]) -> list[str]:
    head = Path(command[0]).name if os.path.isabs(command[0]) else command[0]
    return [head, *command[1:]]


def strip_positionals(command: list[str]) -> list[str]:
    """Drop arguments that name test files/ids so explicit node ids can be appended."""
    rest = [a for a in command[1:] if a.startswith("-") or not Path(a.split("::")[0]).exists()]
    return [command[0], *rest]


def find_case(cases: list[Case], nodeid: str) -> Case | None:
    classname, name = nodeid_to_junit(nodeid)
    for c in cases:
        if c.classname == classname and c.name == name:
            return c
    short = [c for c in cases if c.name == name and c.classname.endswith(classname.split(".")[-1])]
    return short[0] if len(short) == 1 else None


class PytestSession:
    """Runs explicit, ordered node-id lists through the user's pytest command."""

    def __init__(self, command: list[str], cwd: Path, extra_env: dict[str, str] | None = None):
        self.command = [
            a for a in command if a not in _NOISY and not re.fullmatch(r"-[qvx]+|--maxfail=\d+", a)
        ]
        self.cwd = cwd
        self.env = {**os.environ, **(extra_env or {})}
        self.runs = 0

    def collect(self) -> list[str]:
        proc = subprocess.run(
            [*self.command, "--collect-only", "-q", "-p", "no:randomly"],
            cwd=self.cwd,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        ids = [
            ln.strip() for ln in proc.stdout.splitlines() if "::" in ln and " " not in ln.strip()
        ]
        if not ids:
            raise HuntError(
                "could not collect any tests with: "
                + " ".join([*self.command, "--collect-only", "-q"])
                + f"\n{proc.stdout[-800:]}{proc.stderr[-800:]}"
            )
        return ids

    def outcome(self, nodeids: list[str], target: str) -> Case:
        tmp = Path(tempfile.mkdtemp(prefix="flakehunt-why-"))
        xml = tmp / "junit.xml"
        try:
            self.runs += 1
            env = {**self.env, "FLAKEHUNT_RUN": str(self.runs)}
            subprocess.run(
                [
                    *self.command,
                    f"--junitxml={xml}",
                    "-p",
                    "no:randomly",
                    "-p",
                    "no:cacheprovider",
                    *nodeids,
                ],
                cwd=self.cwd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            case = find_case(parse_junit(str(xml)), target)
            if case is None:
                raise HuntError(f"{target} did not run (is the node id right?)")
            return case
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _any_fail(
    session: PytestSession, ids: list[str], target: str, tries: int, msgs: list[str]
) -> tuple[int, int]:
    fails = 0
    for _ in range(tries):
        c = session.outcome(ids, target)
        if c.outcome == FAIL:
            fails += 1
            if c.message:
                msgs.append(c.message)
    return fails, tries


def explain(
    command: list[str],
    target: str,
    *,
    cwd: Path,
    runs: int = 10,
    retries: int = 3,
    max_calls: int = 60,
    on_step: Callable[[str], None] | None = None,
) -> WhyResult:
    say = on_step or (lambda _s: None)
    session = PytestSession(command, cwd)
    order = session.collect()
    if target not in order:
        raise HuntError(f"{target} was not collected. Known ids look like: {order[0]}")
    prefix = order[: order.index(target)]
    msgs: list[str] = []

    say(f"running {target} alone x{runs}")
    alone_f, alone_n = _any_fail(session, [target], target, runs, msgs)
    res = WhyResult(target, UNREPRODUCED, alone_f, alone_n, 0, 0, len(prefix), messages=msgs)
    if alone_f:
        res.verdict = ALONE
        return res

    say(f"running {len(prefix)} preceding tests + target x{runs}")
    with_f, with_n = _any_fail(session, [*prefix, target], target, runs, msgs)
    res.with_prefix_fails, res.with_prefix_runs = with_f, with_n
    if not with_f:
        return res

    res.verdict = ORDER

    def fails(subset: list[str]) -> bool:
        local: list[str] = []
        n, _ = _any_fail(session, [*subset, target], target, retries, local)
        return n > 0

    say(f"minimising {len(prefix)} candidates with delta debugging (max {max_calls} probes)")
    minimal, calls, exhausted = ddmin(prefix, fails, max_calls=max_calls)
    res.polluters, res.ddmin_calls, res.exhausted = minimal, calls, exhausted
    res.reproduce = " ".join([*display_command(command), *minimal, target])
    return res


def hint(res: WhyResult) -> tuple[str, str] | None:
    return hint_for(res.messages)
