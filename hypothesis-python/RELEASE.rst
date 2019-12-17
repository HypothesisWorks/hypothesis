RELEASE_TYPE: patch

This release improves Hypothesis's management of the set of test cases it
tracks between runs. It will only do anything if you have :obj:`~hypothesis.Phase.target`
enabled and an example database set.
In those circumstances it should result in a more thorough and faster set of examples
that are tried on each run.
