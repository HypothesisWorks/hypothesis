RELEASE_TYPE: minor

This release significantly improves the data distribution in rule based stateful testing <stateful_testing>,
by using a technique called `Swarm Testing (Groce, Alex, et al. "Swarm testing."
Proceedings of the 2012 International Symposium on Software Testing and Analysis. ACM, 2012.) <https://agroce.github.io/issta12.pdf>`_
to select which rules are run in any given test case. This should allow it to find many issues that it would previously have missed.

This change is likely to be especially beneficial for stateful tests with large numbers of rules.
