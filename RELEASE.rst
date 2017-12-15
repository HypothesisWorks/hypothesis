RELEASE_TYPE: minor

This release adds a new feature: The :ref:`@reproduce_failure <reproduce_failure>`,
designed to make it easy to use Hypothesis's binary format for examples to
reproduce a problem locally without having to share your example database
between machines.

This also changes when seeds are printed:

* They will no longer be printed for
  normal falsifying examples, as there are now adequate ways of reproducing those
  for all cases, so it just contributes noise.
* They will once again be printed when reusing examples from the database, as
  health check failures should now be more reliable in this scenario so it will
  almost always work in this case.

This work was funded by `Smarkets <https://smarkets.com/>`_.
