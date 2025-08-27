# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass, field

import numpy as np

from hypothesis import strategies as st
from hypothesis.extra import numpy as npst


@dataclass(unsafe_hash=True)
class MyTestClass:
    a: int = 1
    b: str = "hello"
    c: np.ndarray = field(default_factory=lambda: np.array([1, 2]))
    d: dict[str, dict[str, float]] = field(default_factory=lambda: {"x": {"y": 1.0}})


dataclass_instance = MyTestClass()
all_compatible_type_elements = (
    st.from_type(type)
    .filter(lambda x: st.from_type(x).supports_find)
    .flatmap(st.from_type)
    .filter(npst._is_comparable)
)
all_scalar_object_elements = st.one_of(
    st.just(dataclass_instance),
    all_compatible_type_elements,
)
all_numpy_dtypes = st.one_of(npst.scalar_dtypes(), npst.array_dtypes())
all_scalar_elements = st.one_of(
    all_numpy_dtypes.flatmap(npst.from_dtype), all_scalar_object_elements
)
all_object_arrays = npst.arrays(
    np.dtype("O"),
    elements=all_scalar_elements,
    shape=npst.array_shapes(min_dims=1, min_side=1),
)
all_elements = st.one_of(all_scalar_elements, all_object_arrays)


def paired_containers_and_elements(container, elements_to_draw_from, *, key=None):
    """Returns a pair of search strategies for a given container and the elements that were put into it.
    Example:
        >>> containers, elements = paired_containers_and_elements(st.lists, st.sampled_from([1, 2, 3]))
        >>> @given(containers, elements)
        ... def test_lists_with_elements(containers, elements):
        ...     assert containers == elements  # This is the simplest case, but it illustrates the pattern.
    """
    key = "" if key is None else f"_{key}"
    elements = st.shared(elements_to_draw_from, key=f"element_pool{key}")
    containers = st.shared(container(elements), key=f"array{key}")
    return containers, containers.flatmap(
        lambda arr: st.lists(elements, min_size=len(arr), max_size=len(arr))
    )


def assert_safe_equals(a, b):
    """Equals but able to deal with NaN and NaT."""
    if not np.all((a == b) | ((a != b) & (a != a) & (b != b))):
        np.testing.assert_array_equal(a, b)  # get nice message
