RELEASE_TYPE: minor

Introduces the :func:`hypothesis.stateful.consumes` function. When defining
a rule in stateful testing, it can be used to mark bundles from which values
should be consumed, i. e. removed after use in the rule. This has been
proposed in :issue:`136`.

Thanks to Jochen Müller for this long-awaited feature.
