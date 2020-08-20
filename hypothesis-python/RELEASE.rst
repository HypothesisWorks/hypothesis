RELEASE_TYPE: patch

This release improves the quality of the shrink passes that Hypothesis learns.
The impact of this should be fairly minor as Hypothesis does not currently
learn shrink passes on user code, but may improve shrink quality slightly.
