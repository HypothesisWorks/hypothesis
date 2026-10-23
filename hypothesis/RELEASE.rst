RELEASE_TYPE: patch

This patch makes Hypothesis faster: generating test cases takes roughly a third
less time, shrinking failing examples is roughly twice as fast, and
``import hypothesis`` is about 20% faster.
