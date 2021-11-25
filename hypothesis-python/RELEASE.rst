RELEASE_TYPE: minor

This release modifies our :pypi:`pytest` plugin, to avoid importing Hypothesis
and therefore triggering :ref:`Hypothesis' entry points <entry-points>` for
test suites where Hypothesis is installed but not actually used (:issue:`3140`).

If you :ref:`manually load the plugin <disabling-pytest-plugin>`, you'll need
to update the module name accordingly.
