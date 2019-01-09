RELEASE_TYPE: patch

This release improves some internal logic about when a test case in Hypothesis's internal representation could lead to a valid test case.
In some circumstances this can lead to a significant speed up during shrinking.
It may have some minor negative impact on the quality of the final result due to certain shrink passes now having access to less information about test cases in some circumstances, but this should rarely matter.
