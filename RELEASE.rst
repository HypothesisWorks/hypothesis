RELEASE_TYPE: patch

This release changes Hypothesis's caching approach for functions in
:module:`hypothesis.strategies`. Previously it would have cached extremely
aggressively and cache entries would never be evicted. Now it adopts a
least-frequently used, least recently used key invalidation policy, and is
somewhat more conservative about which strategies it caches.

This should cause some workloads (anything that creates strategies based on
dynamic values, e.g. using flatmap or composite) to see a significantly lower
memory usage.
