=============
Health checks
=============

Hypothesis tries to detect common mistakes and things that will cause difficulty
at run time in the form of a number of 'health checks'.

These include detecting and warning about:

* Strategies with very slow data generation
* Strategies which filter out too much
* Recursive strategies which branch too much
* Use of the global random module

If any of these scenarios are detected, Hypothesis will emit a warning about them.

The general goal of these health checks is to warn you about things that you are doing that might
appear to work but will either cause Hypothesis to not work correctly or to perform badly.

To selectively disable health checks, use the suppress_health_check settings.
The argument for this parameter is a list with elements drawn from any of
the class-level attributes of the HealthCheck class.

To disable all health checks, set the perform_health_check settings parameter
to False.
