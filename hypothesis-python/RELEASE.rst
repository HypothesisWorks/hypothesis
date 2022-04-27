RELEASE_TYPE: patch
This release fixes deprecation warnings about ``sre_compile`` / ``sre_parse`` imports and ``importlib.resources`` usage when running Hypothesis on Python 3.11.

It also ensures that Hypothesis' test suite runs with warnings turned into errors, so that such issues will be discovered earlier in the future. This uncovered a couple of formerly hidden minor issues with the testsuite, which are now fixed as well.

Thanks to Florian Bruhin for this contribution.
