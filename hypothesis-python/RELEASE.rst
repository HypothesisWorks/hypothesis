RELEASE_TYPE: patch

This patch fixes a rare internal error in strategies for a list of
unique items sampled from a short non-unique sequence (:issue:`2247`).
The bug was discovered via :pypi:`hypothesis-jsonschema`.
