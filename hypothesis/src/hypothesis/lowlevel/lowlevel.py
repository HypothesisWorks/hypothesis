# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math
from collections.abc import Iterator
from typing import TYPE_CHECKING

from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.utils import _calc_p_continue, calc_label_from_name
from hypothesis.internal.validation import check_type, check_valid_sizes

if TYPE_CHECKING:
    from hypothesis.internal.conjecture.data import ConjectureData
    from hypothesis.strategies import SearchStrategy


_ONE_FROM_MANY_LABEL = calc_label_from_name("one more from many()")
_INTERLEAVED_MANY_MSG = (
    "Iteration over many() is interleaved with other draws.  Are you iterating "
    "over several many() objects at once, e.g. with zip()?"
)


def weighted_booleans(*, p: float) -> "SearchStrategy[bool]":
    """
    Generates a boolean which is ``True`` with probability ``p``.

    |weighted_booleans| is a low-level alternative to |st.booleans|. |st.booleans| is
    roughly equivalent to ``weighted_booleans(p=0.5)``.

    ``p`` must be between 0 and 1 inclusive. If ``0``, only ``False`` will be generated.
    If ``True``, only ``True`` will be generated.

    Note that ``p`` is a hint to Hypothesis rather than a guarantee. It is mostly
    respected during the |Phase.generate| phase, but may be ignored by other phases, such
    as |Phase.shrink| and |Phase.reuse|.
    """
    from hypothesis.strategies._internal.misc import WeightedBooleansStrategy

    check_type((int, float), p, "p")
    if not 0 <= p <= 1:
        raise InvalidArgument(f"p={p!r} must be between 0 and 1 inclusive")
    return WeightedBooleansStrategy(p)


class many:
    """
    |many| provides low-level control over collection sizing. |many| is an abstract way
    to ask for some action to be done some random number of times, while giving some
    control over the distribution of that number.

    |many| is a context manager, which returns an iterator that iterates the same
    number of times as the size it determines. One typical way to use |many| is by
    iterating over it, drawing an element each time:

    .. code-block:: python

        @st.composite
        def custom_int_list(draw):
            lst = []
            with many(min_size=20) as elements:
                for _ in elements:
                    lst.append(draw(st.integers()))
            return lst

    The ``min_size``, ``max_size``, and ``average_size`` parameters control the
    distribution of the number of iterations. By default, ``min_size`` is ``0``,
    ``max_size`` is unbounded, and ``average_size`` is selected as some reasonable midpoint
    between the two.

    As an example of these parameters, to bias towards larger lists than Hypothesis does
    by default, one might write:

    .. code-block:: python

        @st.composite
        def large_lists(draw):
            with many(average_size=20) as elements:
                return [draw(st.integers()) for _ in elements]

    which will return many length-20 lists, some length-15 and length-25 lists, fewer
    length-10 and length-30 lists, and so on.

    Each |many| can be entered once and iterated once, inside its ``with`` block.
    Iterating over several |many| objects at the same time, for example with
    ``zip``, is an error.

    Rejecting elements
    ------------------

    Calling |many.reject| inside the loop marks any choices made during this iteration
    of |many| as not relevant to the |test case|. See |many.reject| for details.

    Stopping early
    --------------

    Leaving the loop early with ``break``, ``return``, or an exception is supported.
    This is useful to forcefully end a |many|, for example if the maximum size depends
    on the drawn elements and cannot be determined ahead of time:

    .. code-block:: python

        with many() as elements:
            for _ in elements:
                n = draw(st.integers())
                if n == 0:
                    break

    Stopping early with fewer than ``min_size`` elements marks the test case as
    invalid, just like a failed |assume|.
    """

    def __init__(
        self,
        *,
        min_size: int = 0,
        max_size: int | None = None,
        average_size: int | float | None = None,
        _data: "ConjectureData | None" = None,
        _observe: bool = True,
    ) -> None:
        check_valid_sizes(min_size, max_size)
        if max_size is None:
            max_size = math.inf
        if average_size is None:
            average_size = min(
                max(min_size * 2, min_size + 5), 0.5 * (min_size + max_size)
            )
        elif not min_size <= average_size <= max_size:
            raise InvalidArgument(
                f"average_size={average_size!r} must be between "
                f"min_size={min_size!r} and max_size={max_size!r}"
            )
        elif min_size != max_size and average_size in (min_size, max_size):
            raise InvalidArgument(
                f"average_size={average_size!r} must not be equal to "
                f"min_size={min_size!r} or max_size={max_size!r}"
            )
        if _data is None:
            from hypothesis.control import current_build_context

            _data = current_build_context().data

        self._data = _data
        self._min_size = min_size
        self._max_size = max_size
        self._p_continue = _calc_p_continue(
            average_size - min_size, max_size - min_size
        )
        self._observe = _observe
        self._count = 0
        self._rejections = 0
        self._force_stop = False
        self._depth: int | None = None
        self._iterated = False
        self._closed = False
        self._done = False
        self._in_element = False
        self._rejected = False

    def __enter__(self) -> "many":
        if self._depth is not None:
            raise InvalidArgument("Cannot reuse a many() object.")
        self._depth = self._data.depth
        return self

    def __exit__(self, exc_type: type | None, *_: object) -> None:
        self._closed = True
        if self._data.frozen:
            return
        if self._data.depth != self._expected_depth():
            if exc_type is None:
                raise InvalidArgument(_INTERLEAVED_MANY_MSG)
            return
        self._finish_element()
        if exc_type is None and not self._done:
            # We exited the loop early, so draw a (forced) stop decision.  This
            # makes our choice sequence look like a natural stop.
            self._force_stop = True
            self._decide()

    def __iter__(self) -> Iterator[None]:
        if self._depth is None or self._closed:
            raise InvalidArgument(
                "many() must be used as `with many(...) as elements:` "
                "followed by `for _ in elements:`, inside the with-block."
            )
        if self._iterated:
            raise InvalidArgument("Cannot iterate over a many() more than once.")
        self._iterated = True
        return self._iterate()

    def _iterate(self) -> Iterator[None]:
        while True:
            if self._closed:
                raise InvalidArgument("Cannot iterate over many() after exiting it.")
            if self._data.depth != self._expected_depth():
                raise InvalidArgument(_INTERLEAVED_MANY_MSG)
            if self._in_element:
                self._finish_element()
            if not self._decide():
                return
            self._count += 1
            self._in_element = True
            self._rejected = False
            yield

    def reject(self, why: str | None = None) -> None:
        """
        Reject the current element of this |many|.

        Calling |many.reject| marks any choices made during this iteration of |many| as
        not relevant to the |test case|. In other words, the Hypothesis engine should
        be able to pretend this iteration did not happen and get equivalent observable
        results to if it did happen.

        This often occurs when requiring some condition on the drawn element before
        adding it to the collection:

        .. code-block:: python

            ret = set()
            with many() as elements:
                for _ in elements:
                    val = draw(st.integers())
                    if val in ret:
                        elements.reject()
                        continue
                    ret.add(val)

        A rejected element does not count towards the size of the |many|. If too many
        elements are rejected, |many| gives up: it stops iterating, or marks the test
        case as invalid if it has not reached ``min_size``.

        Note that |many.reject| is only a performance optimization for the Hypothesis
        engine, as long as the rejected element is not added to your collection. If
        used incorrectly, because the rejected iteration did make an observable
        difference to the generated test case, |many.reject| may actually degrade
        performance of the engine. Use with care!

        If passed, the ``why`` parameter is used as the rejection reason for
        |observability| output.

        |many.reject| can only be called inside the loop, and at most once per
        element.
        """
        if not self._in_element or self._rejected:
            raise InvalidArgument(
                "reject() can only be called once per element, inside the loop."
            )
        self._count -= 1
        self._rejections += 1
        self._rejected = True
        # We set a minimum number of rejections before we give up to avoid
        # failing too fast when we reject the first draw.
        if self._rejections > max(3, 2 * self._count):
            if self._count < self._min_size:
                self._data.mark_invalid(why)
            else:
                self._force_stop = True

    def _expected_depth(self) -> int:
        assert self._depth is not None
        return self._depth + (self._in_element and self._observe)

    def _finish_element(self) -> None:
        if self._in_element:
            self._in_element = False
            if self._observe:
                # A rejected element does not contribute to the collection, so
                # discard its span - the shrinker can then delete it wholesale.
                self._data.stop_span(discard=self._rejected)

    def _decide(self) -> bool:
        if self._force_stop and self._count < self._min_size:
            self._data.mark_invalid(
                f"stopped with {self._count} elements, below min_size={self._min_size}"
            )
        if self._observe:
            self._data.start_span(_ONE_FROM_MANY_LABEL)
        if self._min_size == self._max_size:
            # if we have to hit an exact size, draw unconditionally until that
            # point, and no further.
            should_continue = self._count < self._min_size
        else:
            forced = None
            if self._force_stop:
                forced = False
            elif self._count < self._min_size:
                forced = True
            elif self._count >= self._max_size:
                forced = False
            # Don't enumerate "simplest" choices for this draw, so that probes
            # of collections inside unique collections stop at min_size.
            depth, self._data.unique_element_depth = self._data.unique_element_depth, 0
            should_continue = self._data.draw_boolean(
                self._p_continue, forced=forced, observe=self._observe
            )
            self._data.unique_element_depth = depth
        if not should_continue:
            self._done = True
            if self._observe:
                self._data.stop_span()
        return should_continue
