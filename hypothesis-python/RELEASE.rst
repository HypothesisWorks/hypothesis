RELEASE_TYPE: minor

|@settings| now accepts equivalent string representations for |settings.verbosity|, |settings.phases|, and |settings.suppress_health_check|. For example:

.. code-block:: python

  # these two are now equivalent...
  settings(verbosity=Verbosity.verbose)
  settings(verbosity="verbose")

  # ...as are these two...
  settings(phases=[Phase.explicit])
  settings(phases=["explicit"])

  # ...and these two.
  settings(suppress_health_check=[HealthCheck.filter_too_much])
  settings(suppress_health_check=["filter_too_much"])

This release also changes the canonical value of |Verbosity|, |Phase|, and |HealthCheck| members to a string instead of an integer. For example, ``Phase.reuse.value == "explicit"`` as of this release, where previously ``Phase.reuse.value == 1``.

Instantiating |Verbosity|, |Phase|, or |HealthCheck| with an integer, such as ``Verbosity(0)``, is now deprecated.
