RELEASE_TYPE: patch

This release should significantly reduce the amount of memory that Hypothesis uses for representing large test cases,
by storing information in a more compact representation and only unpacking it lazily when it is first needed.
