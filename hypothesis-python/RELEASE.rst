RELEASE_TYPE: patch

In order to de-flake ``RecursionError`` failures, Hypothesis sets a deterministic limit on ``sys.setrecursionlimit``. This patch makes the setting of this limit aware of uses by Hypothesis from multiple threads, so it does not produce spurious warnings in multithreaded environments.
