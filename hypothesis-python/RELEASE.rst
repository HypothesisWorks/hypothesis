RELEASE_TYPE: patch

This release makes some micro-optimisations within Hypothesis's internal representation of test cases.
This should cause heavily nested test cases to allocate less during generation and shrinking,
which should speed things up slightly.
