# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import _hypothesis_pytestplugin

import hypothesis.extra.pytestplugin


def test_stub_reexports_plugin_hooks():
    # Users who manually load our plugin do so via this stub module.
    assert (
        hypothesis.extra.pytestplugin.pytest_configure
        is _hypothesis_pytestplugin.pytest_configure
    )
