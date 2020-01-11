RELEASE_TYPE: patch

This patch fixes a bug where errors in third-party extensions such as
:pypi:`hypothesis-trio` or :pypi:`hypothesis-jsonschema` were incorrectly
considered to be Hypothesis internal errors, which could result in
confusing error messages.

Thanks to Vincent Michel for reporting and fixing the bug!
