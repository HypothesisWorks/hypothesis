RELEASE_TYPE: minor

Hypothesis now emits deprecation warnings if you use example() inside a
test function or strategy definition (this was never intended to be supported,
but is sufficiently widespread that it warrants a deprecation path).
