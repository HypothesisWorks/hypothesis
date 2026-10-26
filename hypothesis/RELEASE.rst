RELEASE_TYPE: patch

This patch reduces Hypothesis' overhead for each test case. For simple
properties and strategies, generating test cases takes up to a third less time
and shrinking failing examples is up to twice as fast; most tests will see a
smaller improvement. ``import hypothesis`` is also about 20% faster.
