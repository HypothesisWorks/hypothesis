RELEASE_TYPE: patch

This release updates our ``setup.py`` to explicitly check that it is
using a new enough version of :pypi:`setuptools` to support conditional
dependencies (eg :pypi:`enum34` is only needed on Python 2).
See :issue:`1091` for a longer discussion of this change.

If in doubt, just `ensure pip, setuptools, and wheel are up to date.
<https://packaging.python.org/tutorials/installing-packages/#ensure-pip-setuptools-and-wheel-are-up-to-date>`_
This only takes one command, and it's good for both your local environment
and the health of the wider Python packaging ecosystem!
