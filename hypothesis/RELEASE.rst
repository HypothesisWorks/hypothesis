RELEASE_TYPE: patch

This patch fixes quadratic-time behaviour when summarising the statistics of a test run, which Hypothesis does for every test when running under :pypi:`pytest`. This avoids an apparent hang after the last test case with a high number of test cases (>100k).
