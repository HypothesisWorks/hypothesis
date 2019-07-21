=============
Health checks
=============

Hypothesis tries to detect common mistakes and things that will cause difficulty
at run time in the form of a number of 'health checks'.

These include detecting and warning about:

* Strategies with very slow data generation
* Strategies which filter out too much
* Recursive strategies which branch too much
* Tests that are unlikely to complete in a reasonable amount of time.

If any of these scenarios are detected, Hypothesis will emit a warning about them.

The general goal of these health checks is to warn you about things that you are doing that might
appear to work but will either cause Hypothesis to not work correctly or to perform badly.

To selectively disable health checks, use the
:obj:`~hypothesis.settings.suppress_health_check` setting.
The argument for this parameter is a list with elements drawn from any of
the class-level attributes of the HealthCheck class.
Using a value of ``HealthCheck.all()`` will disable all health checks.

.. module:: hypothesis
.. autoclass:: HealthCheck
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
