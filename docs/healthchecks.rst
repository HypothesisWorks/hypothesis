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

These health checks are affected by two settings:

* If the strict setting is set to True, these will be exceptions instead of warnings.
* If the perform_health_check setting is set to False, these health checks will be skipped entirely. This is not
  recommended.
