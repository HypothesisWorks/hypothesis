RELEASE_TYPE: minor

This release makes :doc:`stateful testing <stateful>` more likely to tell you
if you do something unexpected and unsupported:

- The :obj:`~hypothesis.HealthCheck.return_value` health check now applies to
  :func:`~hypothesis.stateful.rule` and :func:`~hypothesis.stateful.initialize`
  rules, if they don't have ``target`` bundles, as well as
  :func:`~hypothesis.stateful.invariant`.
- Using a :func:`~hypothesis.stateful.consumes` bundle as a ``target`` is
  deprecated, and will be an error in a future version.

If existing code triggers these new checks, check for related bugs and
misunderstandings - these patterns *never* had any effect.
