RELEASE_TYPE: minor

This update adds the :obj:`~hypothesis.settings.report_multiple_bugs` setting,
which you can use to disable multi-bug reporting and only raise whichever bug
had the smallest minimal example.  This is occasionally useful when using a
debugger or tools that annotate tracebacks via introspection.
