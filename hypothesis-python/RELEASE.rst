RELEASE_TYPE: minor

This release further improves our ``.patch``-file support from
:ref:`version 6.75 <v6.75.0>`, skipping duplicates, tests which use
:func:`~hypothesis.strategies.data` (and don't support
:obj:`@example() <hypothesis.example>`\ ), and various broken edge-cases.

Because :pypi:`libCST` has released version 1.0 which uses the native parser
by default, we no longer set the ``LIBCST_PARSER_TYPE=native`` environment
variable.  If you are using an older version, you may need to upgrade or
set this envvar for yourself.
