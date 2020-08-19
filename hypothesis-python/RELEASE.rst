RELEASE_TYPE: patch

This release improves the performance of some methods in Hypothesis's internal
automaton library. These are currently only lightly used by user code, but
this may result in slightly faster shrinking.
