# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from libcst.codemod import CodemodTest

from hypothesis.extra import codemods


def test_refactor_function_is_idempotent():
    before = (
        "from hypothesis.strategies import complex_numbers\n\n"
        "complex_numbers(None)\n"
    )
    after = codemods.refactor(before)
    assert before.replace("None", "min_magnitude=0") == after
    assert codemods.refactor(after) == after


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


class TestFixPositionalKeywonlyArgs(CodemodTest):
    TRANSFORM = codemods.HypothesisFixPositionalKeywonlyArgs

    def test_substitution(self) -> None:
        before = """
            import hypothesis.strategies as st

            st.floats(0, 1, False, False, 32)
            st.fractions(0, 1, 9)
        """
        after = """
            import hypothesis.strategies as st

            st.floats(0, 1, allow_nan=False, allow_infinity=False, width=32)
            st.fractions(0, 1, max_denominator=9)
        """
        self.assertCodemod(before=before, after=after)

    def test_noop_with_new_floats_kw(self) -> None:
        before = """
            import hypothesis.strategies as st

            st.floats(0, 1, False, False, True, 32, False, False)  # allow_subnormal=True
        """
        self.assertCodemod(before=before, after=before)

    def test_noop_if_unsure(self) -> None:
        before = """
            import random

            if random.getrandbits(1):
                from hypothesis import target
                from hypothesis.strategies import lists as sets

                def fractions(*args):
                    pass

            else:
                from hypothesis import target
                from hypothesis.strategies import fractions, sets

            fractions(0, 1, 9)
            sets(None, 1)
            target(0, 'label')
        """
        after = before.replace("'label'", "label='label'")
        self.assertCodemod(before=before, after=after)

    def test_stateful_rule_noop(self):
        # `rule()(lambda self: None)` is a call with a positional argument, and
        # so we need an additional check that the "func" node is a Name rather than
        # itself being a Call, lest we rewrite the outer instead of the inner.
        # (this may be an upstream bug in metadata processing)
        before = """
            from hypothesis.stateful import RuleBasedStateMachine, rule

            class MultipleRulesSameFuncMachine(RuleBasedStateMachine):
                rule1 = rule()(lambda self: None)
        """
        self.assertCodemod(before=before, after=before)

    def test_kwargs_noop(self):
        before = """
            from hypothesis import target

            kwargs = {"observation": 1, "label": "foobar"}
            target(**kwargs)
        """
        self.assertCodemod(before=before, after=before)

    def test_noop_with_too_many_arguments_passed(self) -> None:
        # If there are too many arguments, we should leave this alone to raise
        # TypeError on older versions instead of deleting the additional args.
        before = """
            import hypothesis.strategies as st

            st.sets(st.integers(), 0, 1, True)
        """
        self.assertCodemod(before=before, after=before)


class TestHealthCheckAll(CodemodTest):
    TRANSFORM = codemods.HypothesisFixHealthCheckAll

    def test_noop_other_attributes(self):
        # Test that calls to other attributes of HealthCheck are not modified
        before = "result = HealthCheck.data_too_large"
        self.assertCodemod(before=before, after=before)

    def test_substitution(self) -> None:
        # Test that HealthCheck.all() is replaced with list(HealthCheck)
        before = "result = HealthCheck.all()"
        after = "result = list(HealthCheck)"
        # self.assertEqual(run_codemod(input_code), expected_code)
        self.assertCodemod(before=before, after=after)


class TestFixCharactersArguments(CodemodTest):
    TRANSFORM = codemods.HypothesisFixCharactersArguments

    def test_substitution(self) -> None:
        for in_, out in codemods.HypothesisFixCharactersArguments._replacements.items():
            before = f"""
                import hypothesis.strategies as st
                st.characters({in_}=...)
            """
            self.assertCodemod(before=before, after=before.replace(in_, out))

    def test_remove_redundant_exclude_categories(self) -> None:
        args = "blacklist_categories=OUT, whitelist_categories=IN"
        before = f"""
                import hypothesis.strategies as st
                st.characters({args})
            """
        self.assertCodemod(before=before, after=before.replace(args, "categories=IN"))
