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
from typing import TYPE_CHECKING, Protocol

from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.utils import _calc_p_continue, calc_label_from_name
from hypothesis.internal.validation import check_type, check_valid_sizes

if TYPE_CHECKING:
    from hypothesis.internal.conjecture.data import ConjectureData
    from hypothesis.strategies import SearchStrategy

_ONE_FROM_MANY_LABEL = calc_label_from_name("one more from many()")


class _Reject(Protocol):
    def __call__(self, why: str | None = None) -> None: ...


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
    over the distribution of that number.

    |many| returns an iterator, which iterates the same number of times as the size it
    determines. One typical way to use |many| is by iterating over it, drawing an
    element each time:

    .. code-block:: python

        @st.composite
        def custom_int_list(draw):
            lst = []
            for _ in many(min_size=20):
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
            return [draw(st.integers()) for _ in many(average_size=20)]

    which will return many length-20 lists, some length-15 and length-25 lists, fewer
    length-10 and length-30 lists, and so on.

    ``reject()`` function
    ---------------------

    Each iteration of |many| yields a ``reject`` function:

    .. code-block:: python

        for reject in many(...): ...

    Calling this function marks any choices made during this iteration of |many| as not
    relevant to the |test case|. In other words, the Hypothesis engine should be able to
    pretend this iteration did not happen and get equivalent observable results to if it
    did happen.

    This often occurs when requiring some condition on the drawn element before adding
    it to the collection:

    .. code-block:: python

        ret = set()
        for reject in many():
            val = draw(st.integers())
            if val in ret:
                reject()
                continue
            ret.add(val)

    Note that ``reject`` is only a performance optimization for the Hypothesis engine.
    The above example would still work correctly if ``reject()`` were removed.

    If used incorrectly, because the rejected iteration did make an observable difference
    to the generated test case, ``reject`` may actually degrade performance of the engine.
    Use with care!

    ``reject`` has the following signature:

    .. code-block:: python

        def __call__(self, why: str | None = None) -> None: ...

    If passed, the ``why`` parameter is used as the rejection reason for
    |observability| output.

    .. warning::

        Do not early-exit out of a |many| iteration, for example by using ``break``. Doing
        so is an invalid use of the |many| API and prevents Hypothesis from performing
        the necessary bookkeeping.

        For example, the following code is *invalid*:

        .. code-block:: python

            for _ in many():
                n = draw(st.integers())
                if n == 0:
                    break  # BAD!

        If you need to forcefully end a |many|, for example because the maximum size
        depends on the drawn elements and cannot be determined ahead of time, see
        |many.finish|.
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
        self._count = 0
        self._rejections = 0
        self._drawn = False
        self._force_stop = False
        self._rejected = False
        self._observe = _observe

    def __iter__(self) -> "many":
        return self

    def finish(self) -> None:
        """
        End this |many|, exiting on the next iteration.

        |many.finish| is useful to forcefully end a |many|, for example if the maximum
        size depends on the drawn elements and cannot be determined ahead of time:

        .. code-block:: python

            elements = many()
            for _ in elements:
                n = draw(st.integers())
                if n == 0:
                    elements.finish()

        A |many| which has had its |many.finish| called will exit on the next iteration.
        """
        self._force_stop = True

    def __next__(self) -> _Reject:
        if self._drawn:
            # A rejected element does not contribute to the collection, so
            # discard its span - the shrinker can then delete it wholesale.
            self._stop_span(discard=self._rejected)
        self._drawn = True
        self._rejected = False

        self._start_span(_ONE_FROM_MANY_LABEL)
        if self._min_size == self._max_size:
            # if we have to hit an exact size, draw unconditionally until that
            # point, and no further.
            should_continue = self._count < self._min_size and not self._force_stop
        else:
            forced = None
            if self._force_stop:
                forced = False
            elif self._count < self._min_size:
                forced = True
            elif self._count >= self._max_size:
                forced = False
            should_continue = self._data.draw_boolean(
                self._p_continue, forced=forced, observe=self._observe
            )

        if should_continue:
            self._count += 1
            return self._reject
        else:
            self._stop_span()
            raise StopIteration

    def _reject(self, why: str | None = None) -> None:
        assert self._count > 0
        self._rejected = True
        self._count -= 1
        self._rejections += 1
        # We set a minimum number of rejections before we give up to avoid
        # failing too fast when we reject the first draw.
        if self._rejections > max(3, 2 * self._count):
            if self._count < self._min_size:
                self._data.mark_invalid(why)
            else:
                self._force_stop = True

    def _start_span(self, label: int) -> None:
        if self._observe:
            self._data.start_span(label)

    def _stop_span(self, *, discard: bool = False) -> None:
        if self._observe:
            self._data.stop_span(discard=discard)
