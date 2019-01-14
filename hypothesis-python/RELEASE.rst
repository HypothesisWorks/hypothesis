RELEASE_TYPE: patch

This is another release changing the order of certain operations in emergency phases.
These ones primarily affect shrinking examples that involve length-like parameters (e.g. drawing an integer and then drawing that many elements).
In some cases large examples which fit this pattern should now shrink noticeably faster,
but most use cases are likely to be unaffected.
