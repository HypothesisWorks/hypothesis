RELEASE_TYPE: minor

This release drops support for :pypi:`nose`, which ceased development 9 years ago and does not support Python 3.10 or newer.

Hypothesis still supports :pypi:`nose2`. While we do not test ``nose2`` in our CI, we will fix any bugs that get reported.
