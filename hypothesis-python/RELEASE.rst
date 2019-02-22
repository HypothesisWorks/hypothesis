RELEASE_TYPE: patch

This changes the order in which Hypothesis runs certain operations during shrinking.
The main effect should be that it uses significantly less memory on large test cases,
but it may also result in faster (or, hopefully more rarely, slower) shrinking.
