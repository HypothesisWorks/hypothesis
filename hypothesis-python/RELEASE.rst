RELEASE_TYPE: patch

This release changes how Hypothesis manages its search space in cases where it
generates redundant data. This should cause it to generate significantly fewer
duplicated examples (especially with short integer ranges), and may cause it to
produce more useful examples in some cases (especially ones where there is a
significant amount of filtering).
