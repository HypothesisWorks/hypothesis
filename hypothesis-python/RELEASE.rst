RELEASE_TYPE: patch

This release reduces the number of operations the shrinker will try when reordering parts of a test case.
This should in some circumstances significantly speed up shrinking. It *may* result in different final test cases,
and if so usually slightly worse ones, but it should not generally have much impact on the end result as the operations removed were typically useless.
