RELEASE_TYPE: minor

:func:`~hypothesis.strategies.characters` has improved docs about
what arguments are valid, and additional validation logic to raise a
clear error early (instead of e.g. silently ignoring a bad argument).
Categories may be specified as the Unicode 'general category'
(eg ``u'Nd'``), or as the 'major category' (eg ``[u'N', u'Lu']``
is equivalent to ``[u'Nd', u'Nl', u'No', u'Lu']``.

In previous versions, general categories were supported and all other
input was silently ignored.  Now, major categories are supported in
addition to general categories (which may change the behaviour of some
existing code), and all other input is deprecated.
