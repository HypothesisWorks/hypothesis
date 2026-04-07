# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from collections.abc import Buffer
from dataclasses import dataclass

import pytest

from hypothesis import given, strategies as st

from tests.common.debug import find_any


@dataclass
class A:
    constant = 42
    x: int

    # see https://docs.python.org/3/reference/datamodel.html#python-buffer-protocol
    # and https://peps.python.org/pep-0688/
    def __buffer__(self, flags):
        return memoryview(
            self.constant.to_bytes() + self.x.to_bytes(length=32, signed=True)
        )


@given(st.from_type(memoryview[A]))
def test_resolve_bufferlike_memoryview(v):
    assert isinstance(v, memoryview)
    assert v[0] == A.constant
    assert len(v) == 1 + 32


def test_errors_when___buffer___not_implemented():
    class NoBuffer:
        pass

    @given(st.from_type(memoryview[NoBuffer]))
    def f(v):
        pass

    with pytest.raises(
        TypeError, match="a bytes-like object is required, not 'NoBuffer'"
    ):
        f()


def test_resolve_Buffer():
    s = st.from_type(Buffer)
    # on 3.12, we can generate neither. On 3.13, we can generate bytearray, because
    # the removal of ByteString stops blocking bytearray from being the maximal
    # registered type. On 3.14, we can generate both, because memoryview becomes
    # generic.
    find_any(s, lambda v: isinstance(v, memoryview))
    find_any(s, lambda v: isinstance(v, bytearray))
