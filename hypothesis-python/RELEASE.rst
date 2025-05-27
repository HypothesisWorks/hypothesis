RELEASE_TYPE: patch

The observations passed to |TESTCASE_CALLBACKS| are now dataclasses, rather than dictionaries. The content written to ``.hypothesis/observed`` under ``HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY`` remains the same.
