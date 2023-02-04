=============
Health checks
=============

Hypothesis' health checks are designed to detect and warn you about performance
problems where your tests are slow, inefficient, or generating very large examples.

If this is expected, e.g. when generating large arrays or dataframes, you can selectively
disable them with the :obj:`~hypothesis.settings.suppress_health_check` setting.
The argument for this parameter is a list with elements drawn from any of
the class-level attributes of the HealthCheck class.
Using a value of ``HealthCheck.all()`` will disable all health checks.

.. autoclass:: hypothesis.HealthCheck
   :undoc-members:
   :inherited-members:
   :exclude-members: all


.. _deprecation-policy:

------------
Deprecations
------------

We also use a range of custom exception and warning types, so you can see
exactly where an error came from - or turn only our warnings into errors.

.. autoclass:: hypothesis.errors.HypothesisDeprecationWarning

Deprecated features will be continue to emit warnings for at least six
months, and then be removed in the following major release.
Note however that not all warnings are subject to this grace period;
sometimes we strengthen validation by adding a warning and these may
become errors immediately at a major release.
