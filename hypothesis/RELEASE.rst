RELEASE_TYPE: patch

This patch reduces the overhead of running each test case, by up to 10% for
|@given| tests with several arguments, by managing the global :mod:`random`
state more cheaply.
