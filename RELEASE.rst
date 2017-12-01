RELEASE_TYPE: minor

This release adds a new feature: The :ref:`@reproduce_failure <reproduce_failure>`,
designed to make it easy to use Hypothesis's binary format for examples to
reproduce a problem locally without having to share your example database
between machines.

This also changes when seeds are printed - they will no longer be printed for
normal falsifying examples, as there are now adequate ways of reproducing those
for all cases, so it just contributes noise.

This work was funded by `Smarkets <https://smarkets.com/>`_.
