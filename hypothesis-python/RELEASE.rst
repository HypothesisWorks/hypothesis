RELEASE_TYPE: patch

We now use the :pep:`654` `ExceptionGroup <https://docs.python.org/3.11/library/exceptions.html#ExceptionGroup>`__
type - provided by the :pypi:`exceptiongroup` backport on older Pythons -
to ensure that if multiple errors are raised in teardown, they will all propagate.
