# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, strategies as st


class BadRepr:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


Frosty = BadRepr("☃")


def test_just_frosty():
    assert repr(st.just(Frosty)) == "just(☃)"


def test_sampling_snowmen():
    assert repr(st.sampled_from((Frosty, "hi"))) == "sampled_from((☃, 'hi'))"


def varargs(*args, **kwargs):
    pass


@given(
    st.sampled_from(
        [
            "✐",
            "✑",
            "✒",
            "✓",
            "✔",
            "✕",
            "✖",
            "✗",
            "✘",
            "✙",
            "✚",
            "✛",
            "✜",
            "✝",
            "✞",
            "✟",
            "✠",
            "✡",
            "✢",
            "✣",
        ]
    )
)
def test_sampled_from_bad_repr(c):
    pass
