Suppress a health check everywhere
==================================

Hypothesis sometimes raises a |HealthCheck| to indicate that your test may be less effective than you expect, slower than you expect, unlikely to generate effective examples, or otherwise has silently degraded performance.

While |HealthCheck| can be useful to proactively identify issues, you may not care about certain classes of them. If you want to disable a |HealthCheck| everywhere, you can define and load a :ref:`settings profile <settings_profiles>`. Place the following code in any file which is loaded before running your test (or in ``conftest.py``, if using pytest):

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile(
        "my_profile", suppress_health_check=[HealthCheck.filter_too_much]
    )
    settings.load_profile("my_profile")

This profile in particular suppresses the |HealthCheck.filter_too_much| health check for all tests. The exception is if a test has a |@settings| which explicitly sets a different value for ``suppress_health_check``, in which case the profile value will be overridden by the local settings value.

I want to suppress all health checks!
-------------------------------------

.. warning::

    We strongly recommend that you suppress health checks as you encounter them, rather than using a blanket suppression. Several health checks check for subtle interactions that may save you hours of debugging, such as |HealthCheck.function_scoped_fixture| and |HealthCheck.differing_executors|.

If you really want to suppress *all* health checks, for instance to speed up interactive prototyping, you can:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("my_profile", suppress_health_check=list(HealthCheck))
    settings.load_profile("my_profile")
