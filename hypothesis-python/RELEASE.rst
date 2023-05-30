RELEASE_TYPE: patch

This release fixes some ``.patch``-file bugs from :ref:`version 6.75 <v6.75.0>`,
and adds automatic support for writing ``@hypothesis.example()`` or ``@example()``
depending on the current style in your test file - defaulting to the latter.

Note that this feature requires :pypi:`libcst` to be installed, and :pypi:`black`
is strongly recommended.  You can ensure you have the dependencies with
``pip install "hypothesis[cli,codemods]"``.
