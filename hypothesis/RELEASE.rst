RELEASE_TYPE: patch

This patch fixes quadratic-time behaviour when summarising the statistics of a
test run, which Hypothesis does for every test when running under :pypi:`pytest`.
With hundreds of thousands of examples, this could add minutes of apparent hang
after the last example had run.
