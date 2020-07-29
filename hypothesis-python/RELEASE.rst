RELEASE_TYPE: patch

This release adds a heuristic to detect when shrinking has finished despite the fact
that there are many more possible transformations to try. This will be particularly
useful for tests where the minimum failing test case is very large despite there being
many smaller test cases possible, where it is likely to speed up shrinking dramatically.

In some cases it is likely that this will result in worse shrunk test cases. In those
cases rerunning the test will result in further shrinking.
