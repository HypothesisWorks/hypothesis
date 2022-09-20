# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace
from typing import Tuple
from weakref import WeakValueDictionary

import pytest

from hypothesis.errors import HypothesisWarning, InvalidArgument
from hypothesis.extra import array_api
from hypothesis.extra.array_api import (
    NOMINAL_VERSIONS,
    RELEASED_VERSIONS,
    List,
    NominalVersion,
    Optional,
    make_strategies_namespace,
    mock_xp,
)
from hypothesis.strategies import SearchStrategy


@pytest.mark.filterwarnings("ignore::hypothesis.errors.HypothesisWarning")
def test_caching(xp, monkeypatch):
    """Caches namespaces respective to arguments."""
    try:
        hash(xp)
    except TypeError:
        pytest.skip("xp not hashable")
    assert isinstance(array_api._args_to_xps, WeakValueDictionary)
    monkeypatch.setattr(array_api, "_args_to_xps", WeakValueDictionary())
    assert len(array_api._args_to_xps) == 0  # sanity check
    xps1 = array_api.make_strategies_namespace(xp, api_version="2021.12")
    assert len(array_api._args_to_xps) == 1
    xps2 = array_api.make_strategies_namespace(xp, api_version="2021.12")
    assert len(array_api._args_to_xps) == 1
    assert isinstance(xps2, SimpleNamespace)
    assert xps2 is xps1
    del xps1
    del xps2
    assert len(array_api._args_to_xps) == 0


@pytest.mark.filterwarnings("ignore::hypothesis.errors.HypothesisWarning")
def test_complex_dtypes_raises_on_2021_12():
    """Accessing complex_dtypes() for 2021.12 strategy namespace raises helpful
    error, but accessing on future versions returns expected strategy."""
    first_xps = make_strategies_namespace(mock_xp, api_version="2021.12")
    with pytest.raises(AttributeError, match="attempted to access"):
        first_xps.complex_dtypes()
    for api_version in NOMINAL_VERSIONS[1:]:
        xps = make_strategies_namespace(mock_xp, api_version=api_version)
        assert isinstance(xps.complex_dtypes(), SearchStrategy)


class MockArray:
    def __init__(self, supported_versions: Tuple[NominalVersion, ...]):
        assert len(set(supported_versions)) == len(supported_versions)  # sanity check
        self.supported_versions = supported_versions

    def __array_namespace__(self, *, api_version: Optional[NominalVersion] = None):
        if api_version is not None and api_version not in self.supported_versions:
            raise
        return SimpleNamespace(
            __name__="foopy", zeros=lambda _: MockArray(self.supported_versions)
        )


version_permutations: List[Tuple[NominalVersion, ...]] = [
    RELEASED_VERSIONS[:i] for i in range(1, len(RELEASED_VERSIONS) + 1)
]


@pytest.mark.parametrize(
    "supported_versions",
    version_permutations,
    ids=lambda supported_versions: "-".join(supported_versions),
)
def test_version_inferrence(supported_versions):
    """Latest supported api_version is inferred."""
    xp = MockArray(supported_versions).__array_namespace__()
    xps = make_strategies_namespace(xp)
    assert xps.api_version == supported_versions[-1]


def test_raises_on_inferring_with_no_supported_versions():
    """When xp supports no versions, inferring api_version raises helpful error."""
    xp = MockArray(()).__array_namespace__()
    with pytest.raises(InvalidArgument):
        xps = make_strategies_namespace(xp)


@pytest.mark.parametrize(
    ("api_version", "supported_versions"),
    [pytest.param(p[-1], p[:-1], id=p[-1]) for p in version_permutations],
)
def test_warns_on_specifying_unsupported_version(api_version, supported_versions):
    """Specifying an api_version which xp does not support executes with a warning."""
    xp = MockArray(supported_versions).__array_namespace__()
    xp.zeros = None
    with pytest.warns(HypothesisWarning):
        xps = make_strategies_namespace(xp, api_version=api_version)
    assert xps.api_version == api_version
