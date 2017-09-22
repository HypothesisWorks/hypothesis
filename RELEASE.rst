RELEASE_TYPE: patch

This release fixes a bug where when running with use_coverage=True inside an
existing running instance of coverage, Hypothesis would frequently put files
that the coveragerc excluded in the report for the enclosing coverage.
