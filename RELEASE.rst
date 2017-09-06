RELEASE_TYPE: patch

This release improves the reduction of examples involving floating point
numbers to produce more human readable examples.

It also has some general purpose changes to the way the minimizer works
internally, which may see some improvement in quality and slow down of test
case reduction in cases that have nothing to do with floating point numbers.
