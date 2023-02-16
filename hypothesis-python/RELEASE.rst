RELEASE_TYPE: minor

This release turns ``HealthCheck.return_value`` and ``HealthCheck.not_a_test_method``
into unconditional errors, and therefore also deprecates access to those attributes.
(:issue:`3568`).  Thanks to Reagan Lee for the patch!
