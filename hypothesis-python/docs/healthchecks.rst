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

To disable all health checks, set the :obj:`~hypothesis.settings.perform_health_check`
to False.

.. module:: hypothesis
.. autoclass:: HealthCheck
   :undoc-members:
   :inherited-members:
