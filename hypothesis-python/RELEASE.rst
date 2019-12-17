RELEASE_TYPE: patch

This release expands the set of test cases that Hypothesis saves in its
database for future runs to include a representative set of "structurally
different" test cases - e.g. it might try to save test cases where a given list
is empty or not.

Currently this is unlikely to have much user visible impact except to produce
slightly more consistent behaviour between consecutive runs of a test suite.
It is mostly groundwork for future improvements which will exploit this
functionality more effectively.
