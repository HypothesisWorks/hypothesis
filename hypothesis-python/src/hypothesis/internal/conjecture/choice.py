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

from hypothesis.errors import ChoiceTooLarge
from hypothesis.internal.conjecture.floats import float_to_lex, lex_to_float
from hypothesis.internal.conjecture.utils import identity
from hypothesis.internal.floats import make_float_clamper, sign_aware_lte


def _size_to_index(size, *, alphabet_size):
    # this is the closed form of this geometric series:
    # for i in range(size):
    #     index += alphabet_size**i
    if alphabet_size <= 0:
        assert size == 0
        return 0
    if alphabet_size == 1:
        return size
    return (alphabet_size**size - 1) // (alphabet_size - 1)


def _index_to_size(index, alphabet_size):
    if alphabet_size == 0:
        return 0
    elif alphabet_size == 1:
        # there is only one string of each size, so the size is equal to its
        # ordering.
        return index

    # the closed-form inverse of _size_to_index is
    #   size = math.floor(math.log(index * (alphabet_size - 1) + 1, alphabet_size))
    # which is fast, but suffers from float precision errors. As performance is
    # relatively critical here, we'll use this formula by default, but fall back to
    # a much slower integer-only logarithm when the calculation is too close for
    # comfort.
    total = index * (alphabet_size - 1) + 1
    size = math.log(total, alphabet_size)

    # if this computation is close enough that it could have been affected by
    # floating point errors, use a much slower integer-only logarithm instead,
    # which is guaranteed to be precise.
    if 0 < math.ceil(size) - size < 1e-7:
        size = 0
        while total >= alphabet_size:
            total //= alphabet_size
            size += 1
        return size
    return math.floor(size)


def collection_index(choice, *, min_size, alphabet_size, to_order=identity):
    # Collections are ordered by counting the number of values of each size,
    # starting with min_size. alphabet_size indicates how many options there
    # are for a single element. to_order orders an element by returning an n ≥ 0.

    # we start by adding the size to the index, relative to min_size.
    index = _size_to_index(len(choice), alphabet_size=alphabet_size) - _size_to_index(
        min_size, alphabet_size=alphabet_size
    )
    # We then add each element c to the index, starting from the end (so "ab" is
    # simpler than "ba"). Each loop takes c at position i in the sequence and
    # computes the number of sequences of size i which come before it in the ordering.
    for i, c in enumerate(reversed(choice)):
        index += (alphabet_size**i) * to_order(c)
    return index


def collection_value(index, *, min_size, alphabet_size, from_order=identity):
    from hypothesis.internal.conjecture.engine import BUFFER_SIZE_IR

    # this function is probably easiest to make sense of as an inverse of
    # collection_index, tracking ~corresponding lines of code between the two.

    index += _size_to_index(min_size, alphabet_size=alphabet_size)
    size = _index_to_size(index, alphabet_size=alphabet_size)
    # index -> value computation can be arbitrarily expensive for arbitrarily
    # large min_size collections. short-circuit if the resulting size would be
    # obviously-too-large. callers will generally turn this into a .mark_overrun().
    if size >= BUFFER_SIZE_IR:
        raise ChoiceTooLarge

    # subtract out the amount responsible for the size
    index -= _size_to_index(size, alphabet_size=alphabet_size)
    vals = []
    for i in reversed(range(size)):
        # optimization for common case when we hit index 0. Exponentiation
        # on large integers is expensive!
        if index == 0:
            n = 0
        else:
            n = index // (alphabet_size**i)
            # subtract out the nearest multiple of alphabet_size**i
            index -= n * (alphabet_size**i)
        vals.append(from_order(n))
    return vals


def zigzag_index(value, *, shrink_towards):
    # value | 0  1 -1  2 -2  3 -3  4
    # index | 0  1  2  3  4  5  6  7
    index = 2 * abs(shrink_towards - value)
    if value > shrink_towards:
        index -= 1
    return index


def zigzag_value(index, *, shrink_towards):
    assert index >= 0
    # count how many "steps" away from shrink_towards we are.
    n = (index + 1) // 2
    # now check if we're stepping up or down from shrink_towards.
    if (index % 2) == 0:
        n *= -1
    return shrink_towards + n


def choice_to_index(choice, kwargs):
    # This function takes a choice in the choice sequence and returns the
    # complexity index of that choice from among its possible values, where 0
    # is the simplest.
    #
    # Note that the index of a choice depends on its kwargs. The simplest value
    # (at index 0) for {"min_value": None, "max_value": None} is 0, while for
    # {"min_value": 1, "max_value": None} the simplest value is 1.
    #
    # choice_from_index inverts this function. An invariant on both functions is
    # that they must be injective. Unfortunately, floats do not currently respect
    # this. That's not *good*, but nothing has blown up - yet. And ordering
    # floats in a sane manner is quite hard, so I've left it for another day.

    if isinstance(choice, int) and not isinstance(choice, bool):
        # Let a = shrink_towards.
        # * Unbounded: Ordered by (|a - x|, sgn(a - x)). Think of a zigzag.
        #   [a, a + 1, a - 1, a + 2, a - 2, ...]
        # * Semi-bounded: Same as unbounded, except stop on one side when you hit
        #   {min, max}_value. so min_value=-1 a=0 has order
        #   [0, 1, -1, 2, 3, 4, ...]
        # * Bounded: Same as unbounded and semibounded, except stop on each side
        #   when you hit {min, max}_value.
        #
        # To simplify and gain intuition about this ordering, you can think about
        # the most common case where 0 is first (a = 0). We deviate from this only
        # rarely, e.g. for datetimes, where we generally want year 2000 to be
        # simpler than year 0.

        shrink_towards = kwargs["shrink_towards"]
        min_value = kwargs["min_value"]
        max_value = kwargs["max_value"]

        if min_value is not None:
            shrink_towards = max(min_value, shrink_towards)
        if max_value is not None:
            shrink_towards = min(max_value, shrink_towards)

        if min_value is None and max_value is None:
            # case: unbounded
            return zigzag_index(choice, shrink_towards=shrink_towards)
        elif min_value is not None and max_value is None:
            # case: semibounded below

            # min_value = -2
            # index | 0  1  2  3  4  5  6  7
            #     v | 0  1 -1  2 -2  3  4  5
            if abs(choice - shrink_towards) <= (shrink_towards - min_value):
                return zigzag_index(choice, shrink_towards=shrink_towards)
            return choice - min_value
        elif max_value is not None and min_value is None:
            # case: semibounded above
            if abs(choice - shrink_towards) <= (max_value - shrink_towards):
                return zigzag_index(choice, shrink_towards=shrink_towards)
            return max_value - choice
        else:
            # case: bounded

            # range = [-2, 5]
            # shrink_towards = 2
            # index |  0  1  2  3  4  5  6  7
            #     v |  2  3  1  4  0  5 -1 -2
            #
            # ^ with zero weights at index = [0, 2, 6]
            # index |  0  1  2  3  4
            #     v |  3  4  0  5 -2
            assert kwargs["weights"] is None or all(
                w > 0 for w in kwargs["weights"].values()
            ), "technically possible but really annoying to support zero weights"

            # check which side gets exhausted first
            if (shrink_towards - min_value) < (max_value - shrink_towards):
                # Below shrink_towards gets exhausted first. Equivalent to
                # semibounded below
                if abs(choice - shrink_towards) <= (shrink_towards - min_value):
                    return zigzag_index(choice, shrink_towards=shrink_towards)
                return choice - min_value
            else:
                # Above shrink_towards gets exhausted first. Equivalent to semibounded
                # above
                if abs(choice - shrink_towards) <= (max_value - shrink_towards):
                    return zigzag_index(choice, shrink_towards=shrink_towards)
                return max_value - choice
    elif isinstance(choice, bool):
        # Ordered by [False, True].
        p = kwargs["p"]
        if not (2 ** (-64) < p < (1 - 2 ** (-64))):
            # only one option is possible, so whatever it is is first.
            return 0
        return int(choice)
    elif isinstance(choice, bytes):
        return collection_index(
            list(choice),
            min_size=kwargs["min_size"],
            alphabet_size=2**8,
        )
    elif isinstance(choice, str):
        intervals = kwargs["intervals"]
        return collection_index(
            choice,
            min_size=kwargs["min_size"],
            alphabet_size=len(intervals),
            to_order=intervals.index_from_char_in_shrink_order,
        )
    elif isinstance(choice, float):
        sign = int(sign_aware_lte(choice, -0.0))
        return (sign << 64) | float_to_lex(abs(choice))
    else:
        raise NotImplementedError


def choice_from_index(index, ir_type, kwargs):
    assert index >= 0
    if ir_type == "integer":
        shrink_towards = kwargs["shrink_towards"]
        min_value = kwargs["min_value"]
        max_value = kwargs["max_value"]

        if min_value is not None:
            shrink_towards = max(min_value, shrink_towards)
        if max_value is not None:
            shrink_towards = min(max_value, shrink_towards)

        if min_value is None and max_value is None:
            # case: unbounded
            return zigzag_value(index, shrink_towards=shrink_towards)
        elif min_value is not None and max_value is None:
            # case: semibounded below
            if index <= zigzag_index(min_value, shrink_towards=shrink_towards):
                return zigzag_value(index, shrink_towards=shrink_towards)
            return index + min_value
        elif max_value is not None and min_value is None:
            # case: semibounded above
            if index <= zigzag_index(max_value, shrink_towards=shrink_towards):
                return zigzag_value(index, shrink_towards=shrink_towards)
            return max_value - index
        else:
            # case: bounded
            assert kwargs["weights"] is None or all(
                w > 0 for w in kwargs["weights"].values()
            ), "possible but really annoying to support zero weights"

            if (shrink_towards - min_value) < (max_value - shrink_towards):
                # equivalent to semibounded below case
                if index <= zigzag_index(min_value, shrink_towards=shrink_towards):
                    return zigzag_value(index, shrink_towards=shrink_towards)
                return index + min_value
            else:
                # equivalent to semibounded above case
                if index <= zigzag_index(max_value, shrink_towards=shrink_towards):
                    return zigzag_value(index, shrink_towards=shrink_towards)
                return max_value - index
    elif ir_type == "boolean":
        # Ordered by [False, True].
        p = kwargs["p"]
        only = None
        if p <= 2 ** (-64):
            only = False
        elif p >= (1 - 2 ** (-64)):
            only = True

        assert index in {0, 1}
        if only is not None:
            # only one choice
            assert index == 0
            return only
        return bool(index)
    elif ir_type == "bytes":
        value = collection_value(
            index,
            min_size=kwargs["min_size"],
            alphabet_size=2**8,
        )
        return bytes(value)
    elif ir_type == "string":
        intervals = kwargs["intervals"]
        value = collection_value(
            index,
            min_size=kwargs["min_size"],
            alphabet_size=len(intervals),
            from_order=intervals.char_in_shrink_order,
        )
        return "".join(value)
    elif ir_type == "float":
        sign = -1 if index >> 64 else 1
        result = sign * lex_to_float(index & ((1 << 64) - 1))

        clamper = make_float_clamper(
            min_value=kwargs["min_value"],
            max_value=kwargs["max_value"],
            smallest_nonzero_magnitude=kwargs["smallest_nonzero_magnitude"],
            allow_nan=kwargs["allow_nan"],
        )
        return clamper(result)
    else:
        raise NotImplementedError
