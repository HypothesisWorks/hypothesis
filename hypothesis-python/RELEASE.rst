RELEASE_TYPE: minor

Reporting of :obj:`multiple failing examples <hypothesis.settings.report_multiple_bugs>`
now uses the :pep:`654` `ExceptionGroup <https://docs.python.org/3.11/library/exceptions.html#ExceptionGroup>`__ type, which is provided by the
:pypi:`exceptiongroup` backport on Python 3.10 and earlier (:issue:`3175`).
``hypothesis.errors.MultipleFailures`` is therefore deprecated.

Failing examples and other reports are now stored as :pep:`678` exception notes, which
ensures that they will always appear together with the traceback and other information
about their respective error.
