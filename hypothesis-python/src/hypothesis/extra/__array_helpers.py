# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

from typing import Callable, NamedTuple, Optional, Tuple, Union

from hypothesis import assume, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture import utils as cu
from hypothesis.internal.coverage import check_function
from hypothesis.internal.validation import check_type, check_valid_interval
from hypothesis.strategies._internal.utils import defines_strategy

__all__ = [
    "Shape",
    "BroadcastableShapes",
    "BasicIndex",
    "order_check",
    "array_shapes",
    "valid_tuple_axes",
    "broadcastable_shapes",
    "mutually_broadcastable_shapes",
    "make_basic_indices",
]


Shape = Tuple[int, ...]
# We silence flake8 here because it disagrees with mypy about `ellipsis` (`type(...)`)
BasicIndex = Tuple[Union[int, slice, None, "ellipsis"], ...]  # noqa: F821


class BroadcastableShapes(NamedTuple):
    input_shapes: Tuple[Shape, ...]
    result_shape: Shape


@check_function
def order_check(name, floor, min_, max_):
    if floor > min_:
        raise InvalidArgument(f"min_{name} must be at least {floor} but was {min_}")
    if min_ > max_:
        raise InvalidArgument(f"min_{name}={min_} is larger than max_{name}={max_}")


# 32 is a dimension limit specific to NumPy, and does not necessarily apply to
# other array/tensor libraries. Historically these strategies were built for the
# NumPy extra, so it's nice to keep these limits, and it's seemingly unlikely
# someone would want to generate >32 dim arrays anyway.
# See https://github.com/HypothesisWorks/hypothesis/pull/3067.
NDIM_MAX = 32


@check_function
def check_valid_dims(dims, name):
    if dims > NDIM_MAX:
        raise InvalidArgument(
            f"{name}={dims}, but Hypothesis does not support arrays with "
            f"dimensions greater than {NDIM_MAX}"
        )


def array_shapes(
    *,
    min_dims: int = 1,
    max_dims: Optional[int] = None,
    min_side: int = 1,
    max_side: Optional[int] = None,
) -> st.SearchStrategy[Shape]:
    """Return a strategy for array shapes (tuples of int >= 1).

    * ``min_dims`` is the smallest length that the generated shape can possess.
    * ``max_dims`` is the largest length that the generated shape can possess,
      defaulting to ``min_dims + 2``.
    * ``min_side`` is the smallest size that a dimension can possess.
    * ``max_side`` is the largest size that a dimension can possess,
      defaulting to ``min_side + 5``.
    """
    check_type(int, min_dims, "min_dims")
    check_type(int, min_side, "min_side")
    check_valid_dims(min_dims, "min_dims")

    if max_dims is None:
        max_dims = min(min_dims + 2, NDIM_MAX)
    check_type(int, max_dims, "max_dims")
    check_valid_dims(max_dims, "max_dims")

    if max_side is None:
        max_side = min_side + 5
    check_type(int, max_side, "max_side")

    order_check("dims", 0, min_dims, max_dims)
    order_check("side", 0, min_side, max_side)

    return st.lists(
        st.integers(min_side, max_side), min_size=min_dims, max_size=max_dims
    ).map(tuple)


@defines_strategy()
def valid_tuple_axes(
    ndim: int,
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
) -> st.SearchStrategy[Tuple[int, ...]]:
    """All tuples will have a length >= ``min_size`` and <= ``max_size``. The default
    value for ``max_size`` is ``ndim``.

    Examples from this strategy shrink towards an empty tuple, which render most
    sequential functions as no-ops.

    The following are some examples drawn from this strategy.

    .. code-block:: pycon

      >>> [valid_tuple_axes(3).example() for i in range(4)]
      [(-3, 1), (0, 1, -1), (0, 2), (0, -2, 2)]

    ``valid_tuple_axes`` can be joined with other strategies to generate
    any type of valid axis object, i.e. integers, tuples, and ``None``:

    .. code-block:: python

      any_axis_strategy = none() | integers(-ndim, ndim - 1) | valid_tuple_axes(ndim)

    """
    check_type(int, ndim, "ndim")
    check_type(int, min_size, "min_size")
    if max_size is None:
        max_size = ndim
    check_type(int, max_size, "max_size")
    order_check("size", 0, min_size, max_size)
    check_valid_interval(max_size, ndim, "max_size", "ndim")

    axes = st.integers(0, max(0, 2 * ndim - 1)).map(
        lambda x: x if x < ndim else x - 2 * ndim
    )

    return st.lists(
        axes, min_size=min_size, max_size=max_size, unique_by=lambda x: x % ndim
    ).map(tuple)


@defines_strategy()
def broadcastable_shapes(
    shape: Shape,
    *,
    min_dims: int = 0,
    max_dims: Optional[int] = None,
    min_side: int = 1,
    max_side: Optional[int] = None,
) -> st.SearchStrategy[Shape]:
    """Return a strategy for shapes that are broadcast-compatible with the
    provided shape.

    Examples from this strategy shrink towards a shape with length ``min_dims``.
    The size of an aligned dimension shrinks towards size ``1``. The size of an
    unaligned dimension shrink towards ``min_side``.

    * ``shape`` is a tuple of integers.
    * ``min_dims`` is the smallest length that the generated shape can possess.
    * ``max_dims`` is the largest length that the generated shape can possess,
      defaulting to ``max(len(shape), min_dims) + 2``.
    * ``min_side`` is the smallest size that an unaligned dimension can possess.
    * ``max_side`` is the largest size that an unaligned dimension can possess,
      defaulting to 2 plus the size of the largest aligned dimension.

    The following are some examples drawn from this strategy.

    .. code-block:: pycon

        >>> [broadcastable_shapes(shape=(2, 3)).example() for i in range(5)]
        [(1, 3), (), (2, 3), (2, 1), (4, 1, 3), (3, )]

    """
    check_type(tuple, shape, "shape")
    check_type(int, min_side, "min_side")
    check_type(int, min_dims, "min_dims")
    check_valid_dims(min_dims, "min_dims")

    strict_check = max_side is None or max_dims is None

    if max_dims is None:
        max_dims = min(max(len(shape), min_dims) + 2, NDIM_MAX)
    check_type(int, max_dims, "max_dims")
    check_valid_dims(max_dims, "max_dims")

    if max_side is None:
        max_side = max(shape[-max_dims:] + (min_side,)) + 2
    check_type(int, max_side, "max_side")

    order_check("dims", 0, min_dims, max_dims)
    order_check("side", 0, min_side, max_side)

    if strict_check:
        dims = max_dims
        bound_name = "max_dims"
    else:
        dims = min_dims
        bound_name = "min_dims"

    # check for unsatisfiable min_side
    if not all(min_side <= s for s in shape[::-1][:dims] if s != 1):
        raise InvalidArgument(
            f"Given shape={shape}, there are no broadcast-compatible "
            f"shapes that satisfy: {bound_name}={dims} and min_side={min_side}"
        )

    # check for unsatisfiable [min_side, max_side]
    if not (
        min_side <= 1 <= max_side or all(s <= max_side for s in shape[::-1][:dims])
    ):
        raise InvalidArgument(
            f"Given base_shape={shape}, there are no broadcast-compatible "
            f"shapes that satisfy all of {bound_name}={dims}, "
            f"min_side={min_side}, and max_side={max_side}"
        )

    if not strict_check:
        # reduce max_dims to exclude unsatisfiable dimensions
        for n, s in zip(range(max_dims), shape[::-1]):
            if s < min_side and s != 1:
                max_dims = n
                break
            elif not (min_side <= 1 <= max_side or s <= max_side):
                max_dims = n
                break

    return MutuallyBroadcastableShapesStrategy(
        num_shapes=1,
        base_shape=shape,
        min_dims=min_dims,
        max_dims=max_dims,
        min_side=min_side,
        max_side=max_side,
    ).map(lambda x: x.input_shapes[0])


@defines_strategy()
def mutually_broadcastable_shapes(
    num_shapes: int,
    *,
    signature: Optional[BroadcastableShapes] = None,
    base_shape: Shape = (),
    min_dims: int = 0,
    max_dims: Optional[int] = None,
    min_side: int = 1,
    max_side: Optional[int] = None,
) -> st.SearchStrategy[BroadcastableShapes]:
    """Return a strategy for a specified number of shapes N that are
    mutually-broadcastable with one another and with the provided base shape.

    * ``num_shapes`` is the number of mutually broadcast-compatible shapes to generate.
    * ``base_shape`` is the shape against which all generated shapes can broadcast.
      The default shape is empty, which corresponds to a scalar and thus does
      not constrain broadcasting at all.
    * ``shape`` is a tuple of integers.
    * ``min_dims`` is the smallest length that the generated shape can possess.
    * ``max_dims`` is the largest length that the generated shape can possess,
      defaulting to ``max(len(shape), min_dims) + 2``.
    * ``min_side`` is the smallest size that an unaligned dimension can possess.
    * ``max_side`` is the largest size that an unaligned dimension can possess,
      defaulting to 2 plus the size of the largest aligned dimension.

    The strategy will generate a :obj:`python:typing.NamedTuple` containing:

    * ``input_shapes`` as a tuple of the N generated shapes.
    * ``result_shape`` as the resulting shape produced by broadcasting the N shapes
      with the base shape.

    The following are some examples drawn from this strategy.

    .. code-block:: pycon

        >>> # Draw three shapes where each shape is broadcast-compatible with (2, 3)
        ... strat = mutually_broadcastable_shapes(num_shapes=3, base_shape=(2, 3))
        >>> for _ in range(5):
        ...     print(strat.example())
        BroadcastableShapes(input_shapes=((4, 1, 3), (4, 2, 3), ()), result_shape=(4, 2, 3))
        BroadcastableShapes(input_shapes=((3,), (1, 3), (2, 3)), result_shape=(2, 3))
        BroadcastableShapes(input_shapes=((), (), ()), result_shape=(2, 3))
        BroadcastableShapes(input_shapes=((3,), (), (3,)), result_shape=(2, 3))
        BroadcastableShapes(input_shapes=((1, 2, 3), (3,), ()), result_shape=(1, 2, 3))

    """

    if signature is None:
        sig_dims = 0
    else:
        all_shapes = signature.input_shapes + (signature.result_shape,)
        sig_dims = min(len(s) for s in all_shapes)

    check_type(int, num_shapes, "num_shapes")
    if num_shapes < 1:
        raise InvalidArgument(f"num_shapes={num_shapes} must be at least 1")

    check_type(tuple, base_shape, "base_shape")
    check_type(int, min_side, "min_side")
    check_type(int, min_dims, "min_dims")
    check_valid_dims(min_dims, "min_dims")

    strict_check = max_dims is not None

    if max_dims is None:
        max_dims = min(max(len(base_shape), min_dims) + 2, NDIM_MAX - sig_dims)
    check_type(int, max_dims, "max_dims")
    check_valid_dims(max_dims, "max_dims")

    if max_side is None:
        max_side = max(base_shape[-max_dims:] + (min_side,)) + 2
    check_type(int, max_side, "max_side")

    order_check("dims", 0, min_dims, max_dims)
    order_check("side", 0, min_side, max_side)

    if signature is not None and max_dims > NDIM_MAX - sig_dims:
        raise InvalidArgument(
            f"max_dims={max_dims} would exceed the {NDIM_MAX}-dimension "
            "limit Hypothesis imposes on array shapes, given signature="
            f"(input_shapes={signature.input_shapes},"
            f" result_shape={signature.result_shape})"
        )

    if strict_check:
        dims = max_dims
        bound_name = "max_dims"
    else:
        dims = min_dims
        bound_name = "min_dims"

    # check for unsatisfiable min_side
    if not all(min_side <= s for s in base_shape[::-1][:dims] if s != 1):
        raise InvalidArgument(
            f"Given base_shape={base_shape}, there are no broadcast-compatible "
            f"shapes that satisfy: {bound_name}={dims} and min_side={min_side}"
        )

    # check for unsatisfiable [min_side, max_side]
    if not (
        min_side <= 1 <= max_side or all(s <= max_side for s in base_shape[::-1][:dims])
    ):
        raise InvalidArgument(
            f"Given base_shape={base_shape}, there are no broadcast-compatible "
            f"shapes that satisfy all of {bound_name}={dims}, "
            f"min_side={min_side}, and max_side={max_side}"
        )

    if not strict_check:
        # reduce max_dims to exclude unsatisfiable dimensions
        for n, s in zip(range(max_dims), base_shape[::-1]):
            if s < min_side and s != 1:
                max_dims = n
                break
            elif not (min_side <= 1 <= max_side or s <= max_side):
                max_dims = n
                break

    return MutuallyBroadcastableShapesStrategy(
        num_shapes=num_shapes,
        signature=signature,
        base_shape=base_shape,
        min_dims=min_dims,
        max_dims=max_dims,
        min_side=min_side,
        max_side=max_side,
    )


def make_basic_indices(allow_0d_index: bool) -> Callable:
    if allow_0d_index:
        min_index_dim = 0
        min_dims_note = (
            "When ``min_dims == 0``, indices for zero-dimensional arrays are generated."
        )
    else:
        min_index_dim = 1
        min_dims_note = (
            "Indices for zero-dimensional arrays cannot be generated, "
            "so ``min_dims`` must be greater than zero."
        )

    @defines_strategy()
    def basic_indices(
        shape: Shape,
        *,
        min_dims: int = min_index_dim,
        max_dims: Optional[int] = None,
        allow_newaxis: bool = False,
        allow_ellipsis: bool = True,
    ) -> st.SearchStrategy[BasicIndex]:
        # Arguments to exclude scalars, zero-dim arrays, and dims of size zero were
        # all considered and rejected.  We want users to explicitly consider those
        # cases if they're dealing in general indexers, and while it's fiddly we can
        # back-compatibly add them later (hence using kwonlyargs).
        check_type(tuple, shape, "shape")
        if not allow_0d_index and len(shape) == 0:
            raise InvalidArgument("Indices for 0-dimensional arrays are not allowed")
        check_type(bool, allow_ellipsis, "allow_ellipsis")
        check_type(bool, allow_newaxis, "allow_newaxis")
        check_type(int, min_dims, "min_dims")
        check_valid_dims(min_dims, "min_dims")

        if max_dims is None:
            max_dims = min(max(len(shape), min_dims) + 2, NDIM_MAX)
        check_type(int, max_dims, "max_dims")
        check_valid_dims(max_dims, "max_dims")

        order_check("dims", min_index_dim, min_dims, max_dims)

        if not all(isinstance(x, int) and x >= 0 for x in shape):
            raise InvalidArgument(
                f"shape={shape!r}, but all dimensions must be of integer size >= 0"
            )

        return BasicIndexStrategy(
            shape,
            min_dims=min_dims,
            max_dims=max_dims,
            allow_ellipsis=allow_ellipsis,
            allow_newaxis=allow_newaxis,
        )

    basic_indices.__doc__ = f"""
    It generates tuples containing some mix of integers, :obj:`python:slice`
    objects, ``...`` (an ``Ellipsis``), and ``None``. When a length-one tuple
    would be generated, this strategy may instead return the element which will
    index the first axis, e.g. ``5`` instead of ``(5,)``.

    * ``shape`` is the shape of the array that will be indexed, as a tuple of
      positive integers. This must be at least two-dimensional for a tuple to be a
      valid index; for one-dimensional arrays use
      :func:`~hypothesis.strategies.slices` instead.
    * ``min_dims`` is the minimum dimensionality of the resulting array from use of
      the generated index. {min_dims_note}
    * ``max_dims`` is the the maximum dimensionality of the resulting array,
      defaulting to ``max(len(shape), min_dims) + 2``.
    * ``allow_newaxis`` specifies whether ``None`` is allowed in the index.
    * ``allow_ellipsis`` specifies whether ``...`` is allowed in the index.
    """

    return basic_indices


class MutuallyBroadcastableShapesStrategy(st.SearchStrategy):
    def __init__(
        self,
        num_shapes,
        signature=None,
        base_shape=(),
        min_dims=0,
        max_dims=None,
        min_side=1,
        max_side=None,
    ):
        st.SearchStrategy.__init__(self)
        self.base_shape = base_shape
        self.side_strat = st.integers(min_side, max_side)
        self.num_shapes = num_shapes
        self.signature = signature
        self.min_dims = min_dims
        self.max_dims = max_dims
        self.min_side = min_side
        self.max_side = max_side

        self.size_one_allowed = self.min_side <= 1 <= self.max_side

    def do_draw(self, data):
        # We don't usually have a gufunc signature; do the common case first & fast.
        if self.signature is None:
            return self._draw_loop_dimensions(data)

        # When we *do*, draw the core dims, then draw loop dims, and finally combine.
        core_in, core_res = self._draw_core_dimensions(data)

        # If some core shape has omitted optional dimensions, it's an error to add
        # loop dimensions to it.  We never omit core dims if min_dims >= 1.
        # This ensures that we respect Numpy's gufunc broadcasting semantics and user
        # constraints without needing to check whether the loop dims will be
        # interpreted as an invalid substitute for the omitted core dims.
        # We may implement this check later!
        use = [None not in shp for shp in core_in]
        loop_in, loop_res = self._draw_loop_dimensions(data, use=use)

        def add_shape(loop, core):
            return tuple(x for x in (loop + core)[-NDIM_MAX:] if x is not None)

        return BroadcastableShapes(
            input_shapes=tuple(add_shape(l_in, c) for l_in, c in zip(loop_in, core_in)),
            result_shape=add_shape(loop_res, core_res),
        )

    def _draw_core_dimensions(self, data):
        # Draw gufunc core dimensions, with None standing for optional dimensions
        # that will not be present in the final shape.  We track omitted dims so
        # that we can do an accurate per-shape length cap.
        dims = {}
        shapes = []
        for shape in self.signature.input_shapes + (self.signature.result_shape,):
            shapes.append([])
            for name in shape:
                if name.isdigit():
                    shapes[-1].append(int(name))
                    continue
                if name not in dims:
                    dim = name.strip("?")
                    dims[dim] = data.draw(self.side_strat)
                    if self.min_dims == 0 and not data.draw_bits(3):
                        dims[dim + "?"] = None
                    else:
                        dims[dim + "?"] = dims[dim]
                shapes[-1].append(dims[name])
        return tuple(tuple(s) for s in shapes[:-1]), tuple(shapes[-1])

    def _draw_loop_dimensions(self, data, use=None):
        # All shapes are handled in column-major order; i.e. they are reversed
        base_shape = self.base_shape[::-1]
        result_shape = list(base_shape)
        shapes = [[] for _ in range(self.num_shapes)]
        if use is None:
            use = [True for _ in range(self.num_shapes)]
        else:
            assert len(use) == self.num_shapes
            assert all(isinstance(x, bool) for x in use)

        for dim_count in range(1, self.max_dims + 1):
            dim = dim_count - 1

            # We begin by drawing a valid dimension-size for the given
            # dimension. This restricts the variability across the shapes
            # at this dimension such that they can only choose between
            # this size and a singleton dimension.
            if len(base_shape) < dim_count or base_shape[dim] == 1:
                # dim is unrestricted by the base-shape: shrink to min_side
                dim_side = data.draw(self.side_strat)
            elif base_shape[dim] <= self.max_side:
                # dim is aligned with non-singleton base-dim
                dim_side = base_shape[dim]
            else:
                # only a singleton is valid in alignment with the base-dim
                dim_side = 1

            for shape_id, shape in enumerate(shapes):
                # Populating this dimension-size for each shape, either
                # the drawn size is used or, if permitted, a singleton
                # dimension.
                if dim_count <= len(base_shape) and self.size_one_allowed:
                    # aligned: shrink towards size 1
                    side = data.draw(st.sampled_from([1, dim_side]))
                else:
                    side = dim_side

                # Use a trick where where a biased coin is queried to see
                # if the given shape-tuple will continue to be grown. All
                # of the relevant draws will still be made for the given
                # shape-tuple even if it is no longer being added to.
                # This helps to ensure more stable shrinking behavior.
                if self.min_dims < dim_count:
                    use[shape_id] &= cu.biased_coin(
                        data, 1 - 1 / (1 + self.max_dims - dim)
                    )

                if use[shape_id]:
                    shape.append(side)
                    if len(result_shape) < len(shape):
                        result_shape.append(shape[-1])
                    elif shape[-1] != 1 and result_shape[dim] == 1:
                        result_shape[dim] = shape[-1]
            if not any(use):
                break

        result_shape = result_shape[: max(map(len, [self.base_shape] + shapes))]

        assert len(shapes) == self.num_shapes
        assert all(self.min_dims <= len(s) <= self.max_dims for s in shapes)
        assert all(self.min_side <= s <= self.max_side for side in shapes for s in side)

        return BroadcastableShapes(
            input_shapes=tuple(tuple(reversed(shape)) for shape in shapes),
            result_shape=tuple(reversed(result_shape)),
        )


class BasicIndexStrategy(st.SearchStrategy):
    def __init__(self, shape, min_dims, max_dims, allow_ellipsis, allow_newaxis):
        self.shape = shape
        self.min_dims = min_dims
        self.max_dims = max_dims
        self.allow_ellipsis = allow_ellipsis
        self.allow_newaxis = allow_newaxis

    def do_draw(self, data):
        # General plan: determine the actual selection up front with a straightforward
        # approach that shrinks well, then complicate it by inserting other things.
        result = []
        for dim_size in self.shape:
            if dim_size == 0:
                result.append(slice(None))
                continue
            strategy = st.integers(-dim_size, dim_size - 1) | st.slices(dim_size)
            result.append(data.draw(strategy))
        # Insert some number of new size-one dimensions if allowed
        result_dims = sum(isinstance(idx, slice) for idx in result)
        while (
            self.allow_newaxis
            and result_dims < self.max_dims
            and (result_dims < self.min_dims or data.draw(st.booleans()))
        ):
            i = data.draw(st.integers(0, len(result)))
            result.insert(i, None)  # Note that `np.newaxis is None`
            result_dims += 1
        # Check that we'll have the right number of dimensions; reject if not.
        # It's easy to do this by construction if you don't care about shrinking,
        # which is really important for array shapes.  So we filter instead.
        assume(self.min_dims <= result_dims <= self.max_dims)
        # This is a quick-and-dirty way to insert ..., xor shorten the indexer,
        # but it means we don't have to do any structural analysis.
        if self.allow_ellipsis and data.draw(st.booleans()):
            # Choose an index; then replace all adjacent whole-dimension slices.
            i = j = data.draw(st.integers(0, len(result)))
            while i > 0 and result[i - 1] == slice(None):
                i -= 1
            while j < len(result) and result[j] == slice(None):
                j += 1
            result[i:j] = [Ellipsis]
        else:
            while result[-1:] == [slice(None, None)] and data.draw(st.integers(0, 7)):
                result.pop()
        if len(result) == 1 and data.draw(st.booleans()):
            # Sometimes generate bare element equivalent to a length-one tuple
            return result[0]
        return tuple(result)
