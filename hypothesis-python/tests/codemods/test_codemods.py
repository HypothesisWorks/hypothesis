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

from libcst.codemod import CodemodTest

from hypothesis.extra import codemods


class TestFixComplexMinMagnitude(CodemodTest):
    TRANSFORM = codemods.HypothesisFixComplexMinMagnitude

    def test_noop(self) -> None:
        before = """
            from hypothesis.strategies import complex_numbers, complex_numbers as cn

            complex_numbers(min_magnitude=1)  # value OK
            complex_numbers(max_magnitude=None)  # different argument

            class Foo:
                def complex_numbers(self, **kw): pass

                complex_numbers(min_magnitude=None)  # defined in a different scope
        """
        self.assertCodemod(before=before, after=before)

    def test_substitution(self) -> None:
        before = """
            from hypothesis.strategies import complex_numbers, complex_numbers as cn

            complex_numbers(min_magnitude=None)  # simple call to fix
            complex_numbers(min_magnitude=None, max_magnitude=1)  # plus arg after
            complex_numbers(allow_infinity=False, min_magnitude=None)  # plus arg before
            cn(min_magnitude=None)  # imported as alias
        """
        self.assertCodemod(before=before, after=before.replace("None", "0"))
