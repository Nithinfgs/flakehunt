# Launch drafts

Nothing here has been posted. Replace `<N>` placeholders with real numbers from your own run
before posting, and only claim what you have measured.

## Show HN

**Title:** Show HN: Flakehunt, find flaky tests and the test that poisons them

I kept hitting two kinds of "flaky" test and treating them the same. Some fail on their own
(timing, ports, randomness). Others pass alone and only fail after an earlier test leaves state
behind, which in a fixed-order suite looks like a permanent failure, so nobody suspects order.

flakehunt runs your test command N times and reads the JUnit XML, so detection works with any
runner that can write it. Always-failing pytest tests get re-run alone to separate "broken"
from "victim". For a victim, `flakehunt why <test>` runs delta debugging over the tests that
ran before it and prints the minimal set that makes it fail, with a one-line repro.

It is standard-library Python, offline, no LLM. `uvx --with pytest --from git+https://github.com/Nithinfgs/flakehunt flakehunt demo` runs a bundled project with planted flakes.

Known limits: `why` is pytest-only so far, it does not model xdist scheduling, and the cause
hints are regex heuristics. I would like to know which runner to support next, and whether the
detection numbers (it prints the odds a flaky test is caught in N runs) are useful or noise.

https://github.com/Nithinfgs/flakehunt

## Reddit (r/Python, r/programming; check each sub's self-promotion rules first)

**Title:** I built a CLI that finds flaky tests and bisects the earlier test that breaks them

Long-running suites at work had tests that failed "sometimes". It turned out half of them were
not flaky at all: they passed alone and failed because some earlier test mutated a global and
never restored it. Retry plugins hide this.

flakehunt does two things. `run` repeats your command N times, reads JUnit XML, and reports
what flips with a per-run strip and normalised failure messages. `why` takes one test and uses
delta debugging (ddmin) to find the minimal set of earlier tests that makes it fail.

It is stdlib-only Python and offline. The bundled demo reproduces the whole flow in ~10s.
It already exists in similar forms (pytest-flakefinder, detect-test-pollution); the difference
is runner-agnostic detection plus automatic triage into intrinsic / broken / order-dependent.

Feedback I want: do the failure-message hints help or mislead on your suite? Which runner should
get a `why` adapter first (jest, go test)? Repo: https://github.com/Nithinfgs/flakehunt

## X / Twitter

**Short:** Half my "flaky" tests were never flaky. They passed alone and failed after an earlier
test leaked state. Built a small CLI that finds the flakes, then bisects the polluting test.
Offline, no deps. https://github.com/Nithinfgs/flakehunt

**Technical:** flakehunt: repeat a suite N times -> JUnit XML -> per-test outcome matrix. Tests
that always fail get re-run alone; "passes alone" means order dependence. `why` runs ddmin over
the earlier tests and returns the minimal polluter set plus a repro command. Stdlib Python.

**Thread:**
1. Two kinds of flaky test: fails alone (timing, ports, randomness) vs passes alone, fails after
   another test leaks state. They need different fixes.
2. In a fixed-order suite the second kind fails *every* run, so it never looks flaky. Run it
   alone and it passes. That mismatch is the tell.
3. flakehunt automates the tell: `run` repeats the suite, reads JUnit, re-runs always-failing
   tests alone.
4. `why` bisects the tests before the victim with delta debugging and prints the minimal set that
   breaks it, in a handful of probes, plus a one-line repro.
5. Honest bits: pytest-only for `why` so far; it prints the odds a flake of a given rate is
   caught in N runs, because 10 runs only catches a 10% flake ~65% of the time.
6. https://github.com/Nithinfgs/flakehunt. Runner recipes and `why` adapters welcome.

## LinkedIn

Retry-on-failure hides flaky tests; it does not fix them. I wrote a small open-source tool,
flakehunt, to go the other way.

It repeats your test command and reads JUnit XML, so it works with any runner that can emit it.
The part I found most useful: a test that fails on every run in a fixed order is often not
broken but a victim of an earlier test leaking state. flakehunt re-runs those alone, and for
pytest it bisects the earlier tests with delta debugging to name the minimal polluter and a repro
command.

Standard-library Python, offline, no AI. It is early: `why` supports pytest only, and the
cause hints are heuristics. If you run jest or Go suites and want to help shape the next
adapter, I would value the feedback. https://github.com/Nithinfgs/flakehunt

## GitHub metadata

- **Description:** Find flaky tests, then find the test that poisons them. Runner-agnostic via JUnit XML; delta-debugging polluter search for pytest. Offline, zero dependencies.
- **Topics:** `flaky-tests`, `testing`, `pytest`, `junit`, `delta-debugging`, `test-pollution`, `developer-tools`, `cli`, `ci`, `python`
