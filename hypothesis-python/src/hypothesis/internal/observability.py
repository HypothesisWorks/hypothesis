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
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional, Union

from hypothesis.configuration import storage_directory
from hypothesis.errors import HypothesisWarning

if TYPE_CHECKING:
    from typing import TypeAlias

    from hypothesis.internal.conjecture.data import ConjectureData, Status


@dataclass
class PredicateCounts:
    satisfied: int = 0
    unsatisfied: int = 0

    def update_count(self, *, condition: bool) -> None:
        if condition:
            self.satisfied += 1
        else:
            self.unsatisfied += 1


@dataclass
class ObservationMetadata:
    traceback: Optional[str]
    reproduction_decorator: Optional[str]
    predicates: dict[str, PredicateCounts]
    backend: dict[str, Any]
    sys_argv: list[str]
    os_getpid: int
    imported_at: float


@dataclass
class BaseObservation:
    type: Literal["test_case", "info", "alert", "error"]
    property: str
    run_start: float


InfoObservationType = Literal["info", "alert", "error"]
TestCaseStatus = Literal["gave_up", "passed", "failed"]


@dataclass
class InfoObservation(BaseObservation):
    type: InfoObservationType
    title: str
    content: Union[str, dict]


@dataclass
class TestCaseObservation(BaseObservation):
    __test__ = False  # no! bad pytest!

    type: Literal["test_case"]
    status: TestCaseStatus
    status_reason: str
    representation: str
    arguments: dict
    how_generated: str
    features: dict
    coverage: Optional[dict[str, list[int]]]
    timing: dict[str, float]
    metadata: ObservationMetadata


Observation: "TypeAlias" = Union[InfoObservation, TestCaseObservation]

#: A list of callback functions for :ref:`observability <observability>`. Whenever
#: a new observation is created, each function in this list will be called with a
#: single value, which is a dictionary representing that observation.
#:
#: You can append a function to this list to receive observability reports, and
#: remove that function from the list to stop receiving observability reports.
#: Observability is considered enabled if this list is nonempty.
TESTCASE_CALLBACKS: list[Callable[[Observation], None]] = []


@contextmanager
def with_observation_callback(
    callback: Callable[[Observation], None],
) -> Generator[None, None, None]:
    TESTCASE_CALLBACKS.append(callback)
    try:
        yield
    finally:
        TESTCASE_CALLBACKS.remove(callback)


def deliver_observation(observation: Observation) -> None:
    for callback in TESTCASE_CALLBACKS:
        callback(observation)


def make_testcase(
    *,
    run_start: float,
    property: str,
    data: "ConjectureData",
    how_generated: str,
    representation: str = "<unknown>",
    arguments: Optional[dict] = None,
    timing: dict[str, float],
    coverage: Optional[dict[str, list[int]]] = None,
    phase: Optional[str] = None,
    backend_metadata: Optional[dict[str, Any]] = None,
    status: Optional[
        Union[TestCaseStatus, "Status"]
    ] = None,  # overrides automatic calculation
    status_reason: Optional[str] = None,  # overrides automatic calculation
    # added to calculated metadata. If keys overlap, the value from this `metadata`
    # is used
    metadata: Optional[dict[str, Any]] = None,
) -> TestCaseObservation:
    from hypothesis.core import reproduction_decorator
    from hypothesis.internal.conjecture.data import Status

    if status_reason is not None:
        pass
    elif data.interesting_origin:
        status_reason = str(data.interesting_origin)
    elif phase == "shrink" and data.status == Status.OVERRUN:
        status_reason = "exceeded size of current best example"
    else:
        status_reason = str(data.events.pop("invalid because", ""))

    status_map: dict[Status, TestCaseStatus] = {
        Status.OVERRUN: "gave_up",
        Status.INVALID: "gave_up",
        Status.VALID: "passed",
        Status.INTERESTING: "failed",
    }

    if status is not None and isinstance(status, Status):
        status = status_map[status]

    return TestCaseObservation(
        type="test_case",
        status=status if status is not None else status_map[data.status],
        status_reason=status_reason,
        representation=representation,
        arguments={
            k.removeprefix("generate:"): v for k, v in (arguments or {}).items()
        },
        how_generated=how_generated,  # iid, mutation, etc.
        features={
            **{
                f"target:{k}".strip(":"): v for k, v in data.target_observations.items()
            },
            **data.events,
        },
        coverage=coverage,
        timing=timing,
        metadata=ObservationMetadata(
            **{
                "traceback": data.expected_traceback,
                "reproduction_decorator": (
                    reproduction_decorator(data.choices) if status == "failed" else None
                ),
                "predicates": dict(data._observability_predicates),
                "backend": backend_metadata or {},
                **_system_metadata(),
                # unpack last so it takes precedence for duplicate keys
                **(metadata or {}),
            }
        ),
        run_start=run_start,
        property=property,
    )


_WROTE_TO = set()


def _deliver_to_file(observation: Observation) -> None:  # pragma: no cover
    from hypothesis.strategies._internal.utils import to_jsonable

    kind = "testcases" if observation.type == "test_case" else "info"
    fname = storage_directory("observed", f"{date.today().isoformat()}_{kind}.jsonl")
    fname.parent.mkdir(exist_ok=True, parents=True)
    _WROTE_TO.add(fname)
    with fname.open(mode="a") as f:
        obs_json: dict[str, Any] = to_jsonable(observation, avoid_realization=False)  # type: ignore
        if obs_json["type"] == "test_case":
            obs_json["metadata"]["sys.argv"] = obs_json["metadata"].pop("sys_argv")
            obs_json["metadata"]["os.getpid()"] = obs_json["metadata"].pop("os_getpid")
        f.write(json.dumps(obs_json) + "\n")


_imported_at = time.time()


@lru_cache
def _system_metadata() -> dict[str, Any]:
    return {
        "sys_argv": sys.argv,
        "os_getpid": os.getpid(),
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
