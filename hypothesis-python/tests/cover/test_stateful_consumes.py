# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import settings as Settings, strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    consumes,
    initialize,
    rule,
    run_state_machine_as_test,
)


def test_flatmap_consumed_bundle():
    class Machine(RuleBasedStateMachine):
        my_bundle = Bundle("my_bundle")

        @initialize(target=my_bundle)
        def set_initial(self, /) -> str:
            return "sample text"

        @rule(
            character=consumes(my_bundle).flatmap(lambda value: st.sampled_from(value))
        )
        def check(self, /, *, character: str):
            assert isinstance(character, str)
            assert len(character) == 1

    Machine.TestCase.settings = Settings(stateful_step_count=1, max_examples=10)
    run_state_machine_as_test(Machine)
