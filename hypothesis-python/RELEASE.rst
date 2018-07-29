RELEASE_TYPE: patch

This release adds an additional shrink pass that is able to reduce the size of
examples in some cases where the transformation is non-obvious. In particular
this will improve the quality of some examples which would have regressed in
`3.66.12 <3.66.12>`.
