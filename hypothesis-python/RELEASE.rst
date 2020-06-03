RELEASE_TYPE: minor

This release teaches Hypothesis to :ref:`shorten tracebacks <v3.79.2>` for
:ref:`explicit examples <providing-explicit-examples>`, as we already do
for generated examples, so that you can focus on your code rather than ours.

If you have multiple failing explicit examples, they will now all be reported.
To report only the first failure, you can use the :obj:`report_multiple_bugs=False
<hypothesis.settings.report_multiple_bugs>` setting as for generated examples.
