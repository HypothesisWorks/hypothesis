# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Observability tools to spit out analysis-ready tables, one row per test case."""

import json
import os
import sys
import time
import warnings
from datetime import date, timedelta
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Optional, TypedDict

from hypothesis.configuration import storage_directory
from hypothesis.errors import HypothesisWarning

if TYPE_CHECKING:
    from hypothesis.internal.conjecture.data import ConjectureData

#: A list of callback functions for :ref:`observability <observability>`. Whenever
#: a new observation is created, each function in this list will be called with a
#: single value, which is a dictionary representing that observation.
#:
#: You can append a function to this list to receive observability reports, and
#: remove that function from the list to stop receiving observability reports.
#: Observability is considered enabled if this list is nonempty.
TESTCASE_CALLBACKS: list[Callable[[dict], None]] = []


def deliver_json_blob(value: dict) -> None:
    for callback in TESTCASE_CALLBACKS:
        callback(value)


class PredicateCounts(TypedDict):
    satisfied: int
    unsatisfied: int


def make_testcase(
    *,
    start_timestamp: float,
    test_name_or_nodeid: str,
    data: "ConjectureData",
    how_generated: str,
    string_repr: str = "<unknown>",
    arguments: Optional[dict] = None,
    timing: dict[str, float],
    coverage: Optional[dict[str, list[int]]] = None,
    phase: Optional[str] = None,
    backend_metadata: Optional[dict[str, Any]] = None,
) -> dict:
    from hypothesis.core import reproduction_decorator
    from hypothesis.internal.conjecture.data import Status

    if data.interesting_origin:
        status_reason = str(data.interesting_origin)
    elif phase == "shrink" and data.status == Status.OVERRUN:
        status_reason = "exceeded size of current best example"
    else:
        status_reason = str(data.events.pop("invalid because", ""))

    return {
        "type": "test_case",
        "run_start": start_timestamp,
        "property": test_name_or_nodeid,
        "status": {
            Status.OVERRUN: "gave_up",
            Status.INVALID: "gave_up",
            Status.VALID: "passed",
            Status.INTERESTING: "failed",
        }[data.status],
        "status_reason": status_reason,
        "representation": string_repr,
        "arguments": {
            k.removeprefix("generate:"): v for k, v in (arguments or {}).items()
        },
        "how_generated": how_generated,  # iid, mutation, etc.
        "features": {
            **{
                f"target:{k}".strip(":"): v for k, v in data.target_observations.items()
            },
            **data.events,
        },
        "timing": timing,
        "metadata": {
            "traceback": data.expected_traceback,
            "reproduction_decorator": (
                reproduction_decorator(data.choices)
                if data.status is Status.INTERESTING
                else None
            ),
            "predicates": dict(data._observability_predicates),
            "backend": backend_metadata or {},
            **_system_metadata(),
        },
        "coverage": coverage,
    }


_WROTE_TO = set()


def _deliver_to_file(value):  # pragma: no cover
    kind = "testcases" if value["type"] == "test_case" else "info"
    fname = storage_directory("observed", f"{date.today().isoformat()}_{kind}.jsonl")
    fname.parent.mkdir(exist_ok=True, parents=True)
    _WROTE_TO.add(fname)
    with fname.open(mode="a") as f:
        f.write(json.dumps(value) + "\n")


_imported_at = time.time()


@lru_cache
def _system_metadata():
    return {
        "sys.argv": sys.argv,
        "os.getpid()": os.getpid(),
        "imported_at": _imported_at,
    }


#: If ``False``, do not collect coverage information when observability is enabled.
#:
#: This is exposed both for performance (as coverage collection can be slow on
#: Python 3.11 and earlier) and size (if you do not use coverage information,
#: you may not want to store it in-memory).
OBSERVABILITY_COLLECT_COVERAGE = (
    "HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_NOCOVER" not in os.environ
)
if OBSERVABILITY_COLLECT_COVERAGE is False and (
    sys.version_info[:2] >= (3, 12)
):  # pragma: no cover
    warnings.warn(
        "Coverage data collection should be quite fast in Python 3.12 or later "
        "so there should be no need to turn coverage reporting off.",
        HypothesisWarning,
        stacklevel=2,
    )
if "HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY" in os.environ or (
    OBSERVABILITY_COLLECT_COVERAGE is False
):  # pragma: no cover
    TESTCASE_CALLBACKS.append(_deliver_to_file)

    # Remove files more than a week old, to cap the size on disk
    max_age = (date.today() - timedelta(days=8)).isoformat()
    for f in storage_directory("observed", intent_to_write=False).glob("*.jsonl"):
        if f.stem < max_age:  # pragma: no branch
            f.unlink(missing_ok=True)
