RELEASE_TYPE: patch

Improves input validation for several strategies in our :ref:`pandas extra
<hypothesis-pandas>`, so that they raise a helpful ``InvalidArgument`` rather
than ``OverflowError``.

Discovered by our recent :ref:`string generation upgrade <v6.128.0>`.
