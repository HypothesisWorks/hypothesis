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

import base64
import dataclasses
import json
import math
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
    TypeAlias,
    Union,
    cast,
)

from hypothesis.configuration import storage_directory
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.choice import (
    BooleanConstraints,
    BytesConstraints,
    ChoiceConstraintsT,
    ChoiceNode,
    ChoiceT,
    ChoiceTypeT,
    FloatConstraints,
    IntegerConstraints,
    StringConstraints,
)
from hypothesis.internal.escalation import InterestingOrigin
from hypothesis.internal.floats import float_to_int
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.internal.validation import try_convert
from hypothesis.utils.deprecation import note_deprecation

if TYPE_CHECKING:
    from hypothesis.internal.conjecture.data import ConjectureData, Spans, Status

Observation: TypeAlias = Union["InfoObservation", "TestCaseObservation"]
CallbackThreadT: TypeAlias = Callable[[Observation], None]
# for all_threads=True, we pass the thread id as well.
CallbackAllThreadsT: TypeAlias = Callable[[Observation, int], None]
CallbackT: TypeAlias = CallbackThreadT | CallbackAllThreadsT


_WROTE_TO = set()
_deliver_to_file_lock = Lock()


def _deliver_to_file(observation: Observation) -> None:  # pragma: no cover
    from hypothesis.strategies._internal.utils import to_jsonable

    kind = "testcases" if observation.type == "test_case" else "info"
    fname = storage_directory("observed", f"{date.today().isoformat()}_{kind}.jsonl")
    fname.parent.mkdir(exist_ok=True, parents=True)

    observation_bytes = (
        json.dumps(to_jsonable(observation, avoid_realization=False)) + "\n"
    )
    # only allow one conccurent file write to avoid write races. This is likely to make
    # HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY quite slow under threading. A queue
    # would be an improvement, but that requires a background thread, and I
    # would prefer to avoid a thread in the single-threaded case. We could
    # switch over to a queue if we detect multithreading, but it's tricky to get
    # right.
    with _deliver_to_file_lock:
        _WROTE_TO.add(fname)
        with fname.open(mode="a") as f:
            f.write(observation_bytes)


@dataclass(slots=True, frozen=False)
class ObservabilityConfig:
    """
    Options for the |settings.observability| argument to |@settings|.

    Parameters
    ----------

    coverage : bool
        Include the ``coverage`` field in test case observations.
    choices : bool
        Include the ``metadata.choice_nodes`` and ``metadata.choice_spans``
        fields in test case observations.
    callbacks : Collection[Callable]
        Observability callbacks. Each callback will be called for each observation
        this test produces. See :ref:`observability <observability>` for details.

        By default, ``callbacks`` is set to a callback which writes all observations
        to a file in ``.hypothesis/observed``.
    """

    coverage: bool = True
    choices: bool = False
    callbacks: tuple[Callable, ...] = field(default=(_deliver_to_file,))

    def __post_init__(self):
        self.callbacks = try_convert(tuple, self.callbacks, "callbacks")
        if not self.callbacks:
            raise InvalidArgument(
                "Must pass at least one callback to ObservabilityConfig. "
                f"Got: {self!r}."
            )


@dataclass(slots=True, frozen=False)
class PredicateCounts:
    satisfied: int = 0
    unsatisfied: int = 0

    def update_count(self, *, condition: bool) -> None:
        if condition:
            self.satisfied += 1
        else:
            self.unsatisfied += 1


def _choice_to_json(choice: ChoiceT | None) -> Any:
    if choice is None:
        return None
    # see the note on the same check in to_jsonable for why we cast large
    # integers to floats.
    if (
        isinstance(choice, int)
        and not isinstance(choice, bool)
        and abs(choice) >= 2**63
    ):
        return ["integer", str(choice)]
    elif isinstance(choice, bytes):
        return ["bytes", base64.b64encode(choice).decode()]
    elif isinstance(choice, float) and math.isnan(choice):
        # handle nonstandard nan bit patterns. We don't need to do this for -0.0
        # vs 0.0 since json doesn't normalize -0.0 to 0.0.
        return ["float", float_to_int(choice)]
    return choice


def choices_to_json(choices: tuple[ChoiceT, ...]) -> list[Any]:
    return [_choice_to_json(choice) for choice in choices]


def _constraints_to_json(
    choice_type: ChoiceTypeT, constraints: ChoiceConstraintsT
) -> dict[str, Any]:
    constraints = constraints.copy()
    if choice_type == "integer":
        constraints = cast(IntegerConstraints, constraints)
        return {
            "min_value": _choice_to_json(constraints["min_value"]),
            "max_value": _choice_to_json(constraints["max_value"]),
            "weights": (
                None
                if constraints["weights"] is None
                # wrap up in a list, instead of a dict, because json dicts
                # require string keys
                else [
                    (_choice_to_json(k), v) for k, v in constraints["weights"].items()
                ]
            ),
            "shrink_towards": _choice_to_json(constraints["shrink_towards"]),
        }
    elif choice_type == "float":
        constraints = cast(FloatConstraints, constraints)
        return {
            "min_value": _choice_to_json(constraints["min_value"]),
            "max_value": _choice_to_json(constraints["max_value"]),
            "allow_nan": constraints["allow_nan"],
            "smallest_nonzero_magnitude": constraints["smallest_nonzero_magnitude"],
        }
    elif choice_type == "string":
        constraints = cast(StringConstraints, constraints)
        assert isinstance(constraints["intervals"], IntervalSet)
        return {
            "intervals": constraints["intervals"].intervals,
            "min_size": _choice_to_json(constraints["min_size"]),
            "max_size": _choice_to_json(constraints["max_size"]),
        }
    elif choice_type == "bytes":
        constraints = cast(BytesConstraints, constraints)
        return {
            "min_size": _choice_to_json(constraints["min_size"]),
            "max_size": _choice_to_json(constraints["max_size"]),
        }
    elif choice_type == "boolean":
        constraints = cast(BooleanConstraints, constraints)
        return {
            "p": constraints["p"],
        }
    else:
        raise NotImplementedError(f"unknown choice type {choice_type}")


def nodes_to_json(nodes: tuple[ChoiceNode, ...]) -> list[dict[str, Any]]:
    return [
        {
            "type": node.type,
            "value": _choice_to_json(node.value),
            "constraints": _constraints_to_json(node.type, node.constraints),
            "was_forced": node.was_forced,
        }
        for node in nodes
    ]


@dataclass(slots=True, frozen=True)
class ObservationMetadata:
    traceback: str | None
    reproduction_decorator: str | None
    predicates: dict[str, PredicateCounts]
    backend: dict[str, Any]
    sys_argv: list[str]
    os_getpid: int
    imported_at: float
    data_status: "Status"
    phase: str
    interesting_origin: InterestingOrigin | None
    choice_nodes: tuple[ChoiceNode, ...] | None
    choice_spans: Optional["Spans"]

    def to_json(self) -> dict[str, Any]:
        data = {
            "traceback": self.traceback,
            "reproduction_decorator": self.reproduction_decorator,
            "predicates": self.predicates,
            "backend": self.backend,
            "sys.argv": self.sys_argv,
            "os.getpid()": self.os_getpid,
            "imported_at": self.imported_at,
            "data_status": self.data_status,
            "phase": self.phase,
            "interesting_origin": self.interesting_origin,
            "choice_nodes": (
                None if self.choice_nodes is None else nodes_to_json(self.choice_nodes)
            ),
            "choice_spans": (
                None
                if self.choice_spans is None
                else [
                    (
                        # span.label is an int, but cast to string to avoid conversion
                        # to float (and loss of precision) for large label values.
                        #
                        # The value of this label is opaque to consumers anyway, so its
                        # type shouldn't matter as long as it's consistent.
                        str(span.label),
                        span.start,
                        span.end,
                        span.discarded,
                    )
                    for span in self.choice_spans
                ]
            ),
        }
        # check that we didn't forget one
        assert len(data) == len(dataclasses.fields(self))
        return data


@dataclass(slots=True, frozen=True)
class BaseObservation:
    type: Literal["test_case", "info", "alert", "error"]
    property: str
    run_start: float


InfoObservationType = Literal["info", "alert", "error"]
TestCaseStatus = Literal["gave_up", "passed", "failed"]


@dataclass(slots=True, frozen=True)
class InfoObservation(BaseObservation):
    type: InfoObservationType
    title: str
    content: str | dict


@dataclass(slots=True, frozen=True)
class TestCaseObservation(BaseObservation):
    __test__ = False  # no! bad pytest!

    type: Literal["test_case"]
    status: TestCaseStatus
    status_reason: str
    representation: str
    arguments: dict
    how_generated: str
    features: dict
    coverage: dict[str, list[int]] | None
    timing: dict[str, float]
    metadata: ObservationMetadata


def observability_enabled() -> bool:
    from hypothesis._settings import settings

    note_deprecation(
        "observability_enabled() is deprecated. To determine whether the user has "
        "enabled observability, we instead recommend checking "
        "`settings().observability is not None`. You may also wish to check "
        "settings().observability.callbacks, in case a user passes an observability "
        "config with no callbacks. See the settings.observability docs for details.",
        since="RELEASEDAY",
        stacklevel=1,
        has_codemod=False,
    )
    return settings().observability is not None


def make_testcase(
    *,
    run_start: float,
    property: str,
    data: "ConjectureData",
    how_generated: str,
    representation: str = "<unknown>",
    timing: dict[str, float],
    arguments: dict | None = None,
    coverage: dict[str, list[int]] | None = None,
    phase: str | None = None,
    backend_metadata: dict[str, Any] | None = None,
    status: (
        Union[TestCaseStatus, "Status"] | None
    ) = None,  # overrides automatic calculation
    status_reason: str | None = None,  # overrides automatic calculation
    # added to calculated metadata. If keys overlap, the value from this `metadata`
    # is used
    metadata: dict[str, Any] | None = None,
    # observability settings from settings.observability
    observability: ObservabilityConfig | None,
) -> TestCaseObservation:
    from hypothesis.core import reproduction_decorator
    from hypothesis.internal.conjecture.data import Status

    # We should only be sending observability reports for datas that have finished
    # being modified.
    assert data.frozen

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
    if status is None:
        status = status_map[data.status]

    return TestCaseObservation(
        type="test_case",
        status=status,
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
        coverage=coverage if observability and observability.coverage else None,
        timing=timing,
        metadata=ObservationMetadata(
            **{
                "traceback": data.expected_traceback,
                "reproduction_decorator": (
                    reproduction_decorator(data.choices) if status == "failed" else None
                ),
                "predicates": dict(data._observability_predicates),
                "backend": backend_metadata or {},
                "data_status": data.status,
                "phase": phase,
                "interesting_origin": data.interesting_origin,
                "choice_nodes": (
                    data.nodes if observability and observability.choices else None
                ),
                "choice_spans": (
                    data.spans if observability and observability.choices else None
                ),
                **_system_metadata(),
                # unpack last so it takes precedence for duplicate keys
                **(metadata or {}),
            }
        ),
        run_start=run_start,
        property=property,
    )


_imported_at = time.time()


@lru_cache
def _system_metadata() -> dict[str, Any]:
    return {
        "sys_argv": sys.argv,
        "os_getpid": os.getpid(),
        "imported_at": _imported_at,
    }


envvar_observability: ObservabilityConfig | None = None

# supported for backwards compat. These two were always marked experimental, so
# they can be removed whenever. 6 months would be more than generous.
if (
    envvar_value := os.environ.get("HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY")
) is not None:  # pragma: no cover
    note_deprecation(
        "the HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY environment variable is "
        "deprecated. Use either @settings(observability=...), or the "
        "HYPOTHESIS_OBSERVABILITY environment variable instead. "
        "See the observability docs for details.",
        since="RELEASEDAY",
        has_codemod=False,
    )
    envvar_observability = ObservabilityConfig()

if (
    envvar_value := os.environ.get("HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_CHOICES")
) is not None:  # pragma: no cover
    note_deprecation(
        "the HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_CHOICES environment variable is "
        "deprecated. Use @settings(observability=ObservabilityConfig(choices=True)) "
        "instead. See the settings.observability docs for details.",
        since="RELEASEDAY",
        has_codemod=False,
    )
    envvar_observability = ObservabilityConfig(choices=True)

if (
    envvar_value := os.environ.get("HYPOTHESIS_OBSERVABILITY")
) is not None:  # pragma: no cover
    allowed = {"true", "false", "1", "0"}
    if envvar_value.lower() not in allowed:
        raise ValueError(
            f"Got {envvar_value!r} for the HYPOTHESIS_OBSERVABILITY environment "
            f"variable, but expected one of {allowed!r}"
        )
    if envvar_value in {"true", "1"}:
        envvar_observability = ObservabilityConfig()
