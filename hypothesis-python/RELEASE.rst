RELEASE_TYPE: patch

If the :envvar:`HYPOTHESIS_NO_PLUGINS` environment variable is set, we'll avoid 
:ref:`loading plugins <>` such as `the old Pydantic integration 
<https://docs.pydantic.dev/latest/integrations/hypothesis/>`__ or 
`HypoFuzz' CLI options <https://hypofuzz.com/docs/quickstart.html#running-hypothesis-fuzz>`__.

This is probably only useful for our own self-tests, but documented in case it might
help narrow down any particularly weird bugs in complex environments.

