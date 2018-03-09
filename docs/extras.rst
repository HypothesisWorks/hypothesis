===================
Additional packages
===================

Hypothesis itself does not have any dependencies, but there are some packages that
need additional things installed in order to work.

You can install these dependencies using the setuptools extra feature as e.g.
``pip install hypothesis[django]``. This will check installation of compatible versions.

You can also just install hypothesis into a project using them, ignore the version
constraints, and hope for the best.

In general "Which version is Hypothesis compatible with?" is a hard question to answer
and even harder to regularly test. Hypothesis is always tested against the latest
compatible version and each package will note the expected compatibility range. If
you run into a bug with any of these please specify the dependency version.

There are separate pages for :doc:`django` and :doc:`numpy`.

--------------------
hypothesis[pytz]
--------------------

.. automodule:: hypothesis.extra.pytz
   :members:


--------------------
hypothesis[datetime]
--------------------

.. automodule:: hypothesis.extra.datetime
   :members:
