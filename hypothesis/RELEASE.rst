RELEASE_TYPE: patch

This patch fixes the :ref:`codemod <codemods>` for deprecated
:func:`~hypothesis.strategies.characters` arguments, which previously raised
an error when ``**kwargs`` were also passed.
