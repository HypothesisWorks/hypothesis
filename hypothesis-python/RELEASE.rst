RELEASE_TYPE: patch

Fix a spurious warning seen when running pytest's test
suite, caused by never realizing we got out of
initialization due to imbalanced hook calls.
