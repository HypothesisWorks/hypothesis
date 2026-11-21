# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Bias stateful rule selection by relative lines of code.

This implements the heuristic of Holmes, Groce, Pinto, Mittal, Azimi, Kellar
and O'Brien, "Using Relative Lines of Code to Guide Automated Test Generation
for Python" (ACM TOSEM 29(4), 2020), for ``RuleBasedStateMachine``.

For each rule we estimate the number of lines of code "under" it: the summed
size of every distinct Python function entered while the rule runs, counting
each function once per execution, however much of it actually runs.  Rules are
then chosen with probability proportional to that estimate, with rules that
enter no code at all sharing a fixed part of the probability mass, and the
result mixed with the uniform distribution so that no rule is starved.  The
floor matters: rules that run little code often set up state that other rules
need, and without it pure LOC weights can do real harm on such machines.

The weights are measured once and then fixed.  Before the first run of a
machine in a process we run a short *probe* of a few extra examples, with the
usual uniform selection, and then freeze the weights.  This is
required, not just simplest: the weights are part of the constraints on the
integer choice that selects a rule, and the ``DataTree`` requires those to be
identical at a given position on every execution.

The probe observes calls with :mod:`sys.monitoring` where available (3.12+),
using its own tool ID so that it coexists with coverage tools, profilers and
debuggers, and otherwise with :func:`sys.setprofile`, which it never takes
from anybody else.  A rule execution that cannot be observed is simply not
sampled.
"""

import gc
import os
import sys
import threading
from types import CodeType

# Set to False to select stateful rules uniformly, as before.
ENABLED = True
# Examples run by the probe, in addition to max_examples.
PROBE_EXAMPLES = 10
# Below this many max_examples, we do not probe and select uniformly.
MIN_MAX_EXAMPLES = 5 * PROBE_EXAMPLES
# Share of the probability mass spread uniformly over all rules.
FLOOR = 0.25
# Share of the (rest of the) mass shared equally by rules that enter no code.
ZERO_LOC_SHARE = 0.20
# draw_integer(weights=...) requires sum(weights) < 1; the remainder is spent
# on a uniform draw over all rules.
UNIFORM_MIX = 0.01
# draw_integer(weights=...) supports at most this many weighted values.
MAX_WEIGHTED_RULES = 255

# sys.monitoring tool IDs 0, 1, 2 and 5 are reserved by convention for
# debuggers, coverage tools, profilers and optimizers; the scrutineer uses 3.
MONITORING_TOOL_ID = 4
_MONITORING = hasattr(sys, "monitoring")

_HYPOTHESIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
# Frames from this file are Hypothesis's own (zero LOC) but *transparent*: with
# @rule applied outside @precondition, the rule's function is a wrapper defined
# in stateful.py, and the real rule body runs beneath it.
_TRANSPARENT = os.path.join(_HYPOTHESIS_DIR, "stateful.py")

_loc_cache: dict[CodeType, int] = {}


def code_loc(code: CodeType) -> int:  # pragma: no cover  # first call is in a tracer
    """Lines spanned by a code object, or 0 for code we do not count."""
    try:
        return _loc_cache[code]
    except KeyError:
        pass
    if code.co_filename.startswith((_HYPOTHESIS_DIR, "<")):
        # Hypothesis itself, or code with no source file (exec'd: dataclass
        # and namedtuple methods, and the signature-preserving proxies that
        # Hypothesis wraps around rules with preconditions).
        loc = 0
    else:
        first = code.co_firstlineno
        last = max(
            (ln for _, _, ln in code.co_lines() if ln is not None), default=first
        )
        loc = max(1, last - first + 1)
    _loc_cache[code] = loc
    return loc


class LOCProfile:
    """Per-rule samples of LOC entered, gathered during a probe run."""

    def __init__(self) -> None:
        self.samples: dict[str, list[int]] = {}
        self.machine_type: type | None = None
        self._seen: set[CodeType] | None = None
        self._tracer: str | None = None
        self._gc_was_enabled = False
        self._weights: dict[tuple[str, ...], dict[int, float] | None] = {}

    def _make_tracker(self, seen: set[CodeType]):
        """Return (enter, leave) callbacks that add to ``seen`` the code under
        the rule body.  Shared by both tracers, so they measure the same thing.
        """
        # Number of Python frames at or below a Hypothesis-internal frame.
        # Rules that draw (st.data(), or lazily evaluated strategies) run a lot
        # of engine code, which in turn calls into the standard library; none
        # of that is "under" the rule in the sense we care about.
        depth = 0
        # The first user frame entered is the body of the rule; we want the
        # code under it, not the body itself.  Compared by location, not
        # identity: the proxy Hypothesis wraps around a rule with an inner
        # @precondition impersonates the rule's location.
        body: tuple[str, int, str] | None = None

        def enter(code: CodeType) -> None:  # pragma: no cover  # tracer callback
            nonlocal depth, body
            if depth:
                depth += 1
            elif code_loc(code) != 0:
                where = (code.co_filename, code.co_firstlineno, code.co_name)
                if body is None:
                    body = where
                elif where != body:
                    seen.add(code)
            elif code.co_filename != _TRANSPARENT and code.co_filename[:1] != "<":
                depth = 1

        def leave() -> None:  # pragma: no cover  # tracer callback
            nonlocal depth
            if depth:
                depth -= 1

        return enter, leave

    def start(self) -> None:
        self._seen = None
        self._tracer = None
        seen: set[CodeType] = set()
        enter, leave = self._make_tracker(seen)
        # A cyclic collection during the rule runs arbitrary finalizers,
        # weakref callbacks and gc.callbacks, and a few stray lines are enough
        # to move a rule out of the zero-LOC class.  So collection is off, and
        # *before* tracing starts: a collection between the two would have its
        # callbacks taken for the rule body.
        self._gc_was_enabled = gc.isenabled()
        gc.disable()
        if _MONITORING:
            if not self._start_monitoring(enter, leave):  # pragma: no cover
                self._restore_gc()
                return
            self._tracer = "monitoring"
        else:
            if sys.getprofile() is not None:  # pragma: no cover
                # Never clobber somebody else's profiler.
                self._restore_gc()
                return

            def profiler(frame, event, arg):  # pragma: no cover  # tracer callback
                # A resumed generator or coroutine is a "call" and a suspended
                # one a "return", so entries and exits always balance.
                if event == "call":
                    enter(frame.f_code)
                elif event == "return":
                    leave()

            sys.setprofile(profiler)
            self._tracer = "profile"
        self._seen = seen

    def _restore_gc(self) -> None:
        if self._gc_was_enabled:  # pragma: no branch
            gc.enable()

    def _start_monitoring(self, enter, leave) -> bool:
        mon = sys.monitoring
        try:
            mon.use_tool_id(MONITORING_TOOL_ID, "hypothesis-locbias")
        except ValueError:  # pragma: no cover  # somebody else holds our ID
            return False
        # sys.monitoring sees every thread; only the one running the rule
        # counts.
        me = threading.get_ident()
        get_ident = threading.get_ident

        def on_enter(code, offset, *rest):  # pragma: no cover  # tracer callback
            if get_ident() == me:
                enter(code)

        def on_leave(code, offset, arg):  # pragma: no cover  # tracer callback
            if get_ident() == me:
                leave()

        ev = mon.events
        # The same pairing as sys.setprofile's call/return: a frame is entered
        # by starting, resuming, or having an exception thrown into it, and
        # left by returning, yielding, or unwinding.
        for e in (ev.PY_START, ev.PY_RESUME, ev.PY_THROW):
            mon.register_callback(MONITORING_TOOL_ID, e, on_enter)
        for e in (ev.PY_RETURN, ev.PY_YIELD, ev.PY_UNWIND):
            mon.register_callback(MONITORING_TOOL_ID, e, on_leave)
        mon.set_events(
            MONITORING_TOOL_ID,
            ev.PY_START
            | ev.PY_RESUME
            | ev.PY_THROW
            | ev.PY_RETURN
            | ev.PY_YIELD
            | ev.PY_UNWIND,
        )
        return True

    def _stop_tracing(self) -> None:
        if self._tracer == "monitoring":
            mon = sys.monitoring
            mon.set_events(MONITORING_TOOL_ID, 0)
            ev = mon.events
            for e in (
                ev.PY_START,
                ev.PY_RESUME,
                ev.PY_THROW,
                ev.PY_RETURN,
                ev.PY_YIELD,
                ev.PY_UNWIND,
            ):
                mon.register_callback(MONITORING_TOOL_ID, e, None)
            mon.free_tool_id(MONITORING_TOOL_ID)
        elif self._tracer == "profile":  # pragma: no branch  # always tracing here
            sys.setprofile(None)
        self._tracer = None
        # Only after tracing has stopped, for the same reason as in start().
        self._restore_gc()

    def abort(self) -> None:
        if self._seen is not None:
            self._stop_tracing()
            self._seen = None

    def stop(self, rule_name: str) -> None:
        if self._seen is None:  # pragma: no cover  # could not trace
            return
        self._stop_tracing()
        seen, self._seen = self._seen, None
        self.samples.setdefault(rule_name, []).append(sum(map(code_loc, seen)))

    def mean_loc(self) -> dict[str, float]:
        return {k: sum(v) / len(v) for k, v in self.samples.items() if v}

    def weights(self, rule_names: tuple[str, ...]) -> dict[int, float] | None:
        """Map index-in-rule_names to selection probability, or None if we
        have no basis for a non-uniform choice."""
        if rule_names not in self._weights:
            self._weights[rule_names] = self._compute_weights(rule_names)
        return self._weights[rule_names]

    def _compute_weights(self, rule_names: tuple[str, ...]) -> dict[int, float] | None:
        n = len(rule_names)
        if n < 2 or n > MAX_WEIGHTED_RULES:
            return None
        means = self.mean_loc()
        nonzero = [m for m in means.values() if m > 0]
        if not nonzero:
            return None
        # A rule the probe never managed to run (e.g. a hard precondition) gets
        # the average weight: we know nothing, so neither favour nor starve it.
        neutral = sum(nonzero) / len(nonzero)
        loc = [means.get(name, neutral) for name in rule_names]
        zeros = [i for i, x in enumerate(loc) if x == 0]
        total = sum(loc)
        positive_share = 1.0 - ZERO_LOC_SHARE if zeros else 1.0
        probs = {}
        for i, x in enumerate(loc):
            if x == 0:
                p = ZERO_LOC_SHARE / len(zeros)
            else:
                p = positive_share * x / total
            probs[i] = ((1.0 - FLOOR) * p + FLOOR / n) * (1.0 - UNIFORM_MIX)
        return probs


_local = threading.local()
# Frozen profiles, keyed by state machine class.
_PROFILES: dict[type, LOCProfile] = {}
# Factories we have already probed (a factory need not be the machine class).
_PROBED: set[object] = set()


def probing() -> LOCProfile | None:
    """The profile being filled in by a probe run on this thread, if any."""
    return getattr(_local, "profile", None)


def needs_probe(factory: object, max_examples: int) -> bool:
    if not ENABLED or probing() is not None or max_examples < MIN_MAX_EXAMPLES:
        return False
    try:
        return factory not in _PROBED
    except TypeError:  # pragma: no cover  # unhashable factory
        return False


def begin_probe(factory: object) -> LOCProfile:
    _PROBED.add(factory)
    _local.profile = LOCProfile()
    return _local.profile


def end_probe() -> None:
    profile = probing()
    _local.profile = None
    assert profile is not None
    profile.abort()  # in case the probe died mid-rule
    if profile.machine_type is not None:
        _PROFILES.setdefault(profile.machine_type, profile)


def weights_for(
    machine_type: type, rule_names: tuple[str, ...]
) -> dict[int, float] | None:
    if not ENABLED or probing() is not None:
        return None
    profile = _PROFILES.get(machine_type)
    return None if profile is None else profile.weights(rule_names)
