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
from weakref import WeakValueDictionary

import pytest

from hypothesis.extra import array_api
from hypothesis.extra.array_api import (
    NOMINAL_VERSIONS,
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
