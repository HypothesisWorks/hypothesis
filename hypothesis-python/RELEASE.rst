RELEASE_TYPE: minor

Nesting :func:`@given <hypothesis.given>` inside of :func:`@given <hypothesis.given>` is now a :ref:`health check <healthchecks>` failure. Nesting :func:`@given <hypothesis.given>` results in quadratic generation and shrinking behavior, and can usually be more cleanly expressed by replacing the inner function with a :func:`~hypothesis.strategies.data` parameter on the outer given. For more details, see :obj:`~hypothesis.errors.HealthCheck.nested_given`. (:issue:`4167`)
