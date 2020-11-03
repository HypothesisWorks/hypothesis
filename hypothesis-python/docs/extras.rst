======================
First-party extensions
======================

Hypothesis has minimal dependencies, to maximise
compatibility and make installing Hypothesis as easy as possible.

Our integrations with specific packages are therefore provided by ``extra``
modules that need their individual dependencies installed in order to work.
You can install these dependencies using the setuptools extra feature as e.g.
``pip install hypothesis[django]``. This will check installation of compatible versions.

You can also just install hypothesis into a project using them, ignore the version
constraints, and hope for the best.

In general "Which version is Hypothesis compatible with?" is a hard question to answer
and even harder to regularly test. Hypothesis is always tested against the latest
compatible version and each package will note the expected compatibility range. If
you run into a bug with any of these please specify the dependency version.

There are separate pages for :doc:`django` and :doc:`numpy`.


.. automodule:: hypothesis.extra.cli

.. automodule:: hypothesis.extra.dpcontracts
   :members:

.. automodule:: hypothesis.extra.lark
   :members:

Example grammars, which may provide a useful starting point for your tests, can be found
`in the Lark repository <https://github.com/lark-parser/lark/tree/master/examples>`__
and in `this third-party collection <https://github.com/ligurio/grammars>`__.

.. automodule:: hypothesis.extra.pytz
   :members:

.. automodule:: hypothesis.extra.dateutil
   :members:
