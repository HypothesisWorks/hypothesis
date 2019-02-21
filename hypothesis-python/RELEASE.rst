RELEASE_TYPE: minor

Fixes that `hypothesis.extra.numpy.array_shapes` cannot take a zero minimum
dimension or side. We also allow `hypothesis.extra.numpy.arrays` to generate
zero dimensional arrays with iterable objects (e.g., tuples) as their element.
These are blocking issues in pull request #1784.

Thanks to Ryan Turner for this change.
