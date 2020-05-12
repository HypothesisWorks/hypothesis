# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import math
import statistics
from collections import Counter

from hypothesis.utils.dynamicvariables import DynamicVariable

collector = DynamicVariable(None)


def note_statistics(stats_dict):
    callback = collector.value
    if callback is not None:
        callback(stats_dict)


def describe_targets(best_targets):
    """Return a list of lines describing the results of `target`, if any."""
    # These lines are included in the general statistics description below,
    # but also printed immediately below failing examples to alleviate the
    # "threshold problem" where shrinking can make severe bug look trival.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2180
    if not best_targets:
        return []
    elif len(best_targets) == 1:
        label, score = next(iter(best_targets.items()))
        return ["Highest target score: {:g}  (label={!r})".format(score, label)]
    else:
        lines = ["Highest target scores:"]
        for label, score in sorted(best_targets.items(), key=lambda x: x[::-1]):
            lines.append("{:>16g}  (label={!r})".format(score, label))
        return lines


def describe_statistics(stats_dict):
    """Return a multi-line string describing the passed run statistics.

    `stats_dict` must be a dictionary of data in the format collected by
    `hypothesis.internal.conjecture.engine.ConjectureRunner.statistics`.

    We DO NOT promise that this format will be stable or supported over
    time, but do aim to make it reasonably useful for downstream users.
    It's also meant to support benchmarking for research purposes.

    This function is responsible for the report which is printed in the
    terminal for our pytest --hypothesis-show-statistics option.
    """
    lines = [stats_dict["nodeid"] + ":\n"] if "nodeid" in stats_dict else []
    prev_failures = 0
    for phase in ["reuse", "generate", "shrink"]:
        d = stats_dict.get(phase + "-phase", {})
        # Basic information we report for every phase
        cases = d.get("test-cases", [])
        if not cases:
            continue
        statuses = Counter(t["status"] for t in cases)
        runtimes = sorted(t["runtime"] for t in cases)
        n = max(0, len(runtimes) - 1)
        lower = int(runtimes[int(math.floor(n * 0.05))] * 1000)
        upper = int(runtimes[int(math.ceil(n * 0.95))] * 1000)
        if upper == 0:
            ms = "< 1ms"
        elif lower == upper:
            ms = "~ %dms" % (lower,)
        else:
            ms = "%d-%d ms" % (lower, upper)
        drawtime_percent = 100 * statistics.mean(
            t["drawtime"] / t["runtime"] if t["runtime"] > 0 else 0 for t in cases
        )
        lines.append(
            "  - during {} phase ({:.2f} seconds):\n"
            "    - Typical runtimes: {}, ~ {:.0f}% in data generation\n"
            "    - {} passing examples, {} failing examples, {} invalid examples".format(
                phase,
                d["duration-seconds"],
                ms,
                drawtime_percent,
                statuses["valid"],
                statuses["interesting"],
                statuses["invalid"] + statuses["overrun"],
            )
        )
        # If we've found new distinct failures in this phase, report them
        distinct_failures = d["distinct-failures"] - prev_failures
        if distinct_failures:
            plural = distinct_failures > 1
            lines.append(
                "    - Found {}{} failing example{} in this phase".format(
                    distinct_failures, " more" * bool(prev_failures), "s" * plural
                )
            )
        prev_failures = d["distinct-failures"]
        # Report events during the generate phase, if there were any
        if phase == "generate":
            events = Counter(sum((t["events"] for t in cases), []))
            if events:
                lines.append("    - Events:")
                lines += [
                    "      * {:.2f}%, {}".format(100 * v / len(cases), k)
                    for k, v in sorted(events.items(), key=lambda x: (-x[1], x[0]))
                ]
        # Some additional details on the shrinking phase
        if phase == "shrink":
            lines.append(
                "    - Tried {} shrinks of which {} were successful".format(
                    len(cases), d["shrinks-successful"],
                )
            )
        lines.append("")

    target_lines = describe_targets(stats_dict.get("targets", {}))
    if target_lines:
        lines.append("  - " + target_lines[0])
        lines.extend("    " + l for l in target_lines[1:])
    lines.append("  - Stopped because " + stats_dict["stopped-because"])
    return "\n".join(lines)
