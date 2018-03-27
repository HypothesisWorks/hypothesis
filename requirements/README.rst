Hypothesis Dependencies
=======================

TLDR: for local development, create a virtualenv and do:

    pip install --upgrade pip setuptools wheel
    pip install --upgrade --editable .[all,dev]

Why have all this then?
-----------------------

Because pinning your dependencies is a Good Thing, and this makes our
builds (on Travis and other CI systems) reproducible.  We use
`pip-tools <https://pypi.org/project/pip-tools/>`_ to generate a complete
snapshot of our transitive dependencies from the minimal inputs
(ie the .in files, which in turn `delegate to setup.py
<https://caremad.io/posts/2013/07/setup-vs-requirement/>`_).
Finally, https://pyup.io opens a pull request with updates once per week,
so we always test upgrades and still stay up to date.

To trace where the development dependencies get used: look for an install
command in tox.ini, find the associated task in the Makefile, and
(optionally) look it up in the .travis.yml - or the other way around.
