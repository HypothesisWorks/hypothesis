=============
Contributing
=============

First off: It's great that you want to contribute to Hypothesis! Thanks!

---------------------------------------
Just tell me how to make a pull request
---------------------------------------

1. Make your change and ensure it has adequate tests
2. Create ``hypothesis-python/RELEASE.rst`` with ``RELEASE_TYPE: patch``
   for small bugfixes, or ``minor`` for new features.  See ``RELEASE-sample.rst``
   as an example.
3. Add yourself to the list in ``AUTHORS.rst`` and open a PR!

For more detail, read on; for even more, continue to the ``guides/`` directory!

------------------
Ways to Contribute
------------------

Hypothesis is a mature yet active project. This means that there are many
ways in which you can contribute.

For example, it's super useful and highly appreciated if you do any of:

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Give a talk about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo
* Submit PRs

If you build a Hypothesis strategy that you would like to be more widely known
please add it to the list of external strategies by preparing a PR against
the docs/strategies.rst file.

If you find an error in the documentation, please feel free to submit a PR that
fixes the error. Spot a tyop? Fix it up and send us a PR!
You can read more about how we document Hypothesis in ``guides/documentation.rst``

The process for submitting source code PRs is generally more involved
(don't worry, we'll help you through it), so do read the rest of this document.
If you're planning a larger change, the contributor guides (in the ``guides/``
directory) will make sure you're on the right track.

----------------------------------
Installing from source and testing
----------------------------------

If you want to install directly from the source code (e.g. because you want to
make changes and install the changed version) you can do this with:

.. code:: bash

  pip install -r requirements/test.in
  pip install -r requirements/tools.in
  pip install -e hypothesis-python/

  # You don't need to run the tests, but here's the command:
  pytest hypothesis-python/tests/cover/

You may wish to do all of this in a
`virtualenv <https://docs.python.org/3/library/venv.html>`_. For example:

.. code:: bash

  python3 -m venv .venv
  source .venv/bin/activate
  pip install hypothesis

Will create an isolated environment where you can install and try out
Hypothesis without affecting your system packages.

-----------------------
Copyright and Licensing
-----------------------

It's important to make sure that you own the rights to the work you are submitting.
If it is done on work time, or you have a particularly onerous contract, make sure
you've checked with your employer.

All work in Hypothesis is licensed under the terms of the
`Mozilla Public License, version 2.0 <https://mozilla.org/MPL/2.0/>`_. By
submitting a contribution you are agreeing to licence your work under those
terms.

Finally, if it is not there already, add your name (and a link to your GitHub
and email address if you want) to the list of contributors found in
AUTHORS.rst, in alphabetical order. It doesn't have to be your
"real" name (whatever that means), any sort of public identifier
is fine. In particular a GitHub account is sufficient.

-----------------------
The actual contribution
-----------------------

OK, so you want to make a contribution and have sorted out the legalese. What now?

First off: If you're planning on implementing a new feature, talk to us
first! Come `join us on the mailing list <https://hypothesis.readthedocs.io/en/latest/community.html#community>`_,
or open an issue. If it's really small feel free to open a work in progress pull request sketching
out the idea, but it's best to get feedback from the Hypothesis maintainers
before sinking a bunch of work into it.
If you're working on an existing issue, leave a comment so we can try to avoid
duplicating your work before you open a pull request.

In general work-in-progress pull requests are totally welcome if you want early feedback
or help with some of the tricky details. Don't be afraid to ask for help.

In order to get merged, a pull request will have to have a green build (naturally) and
to be approved by a Hypothesis maintainer (and, depending on what it is, possibly specifically
by DRMacIver).  Most pull requests will also need to `write a changelog entry in
hypothesis-python/RELEASE.rst <guides/documentation.rst#changelog-entries>`_.

The review process is the same one that all changes to Hypothesis go through, regardless of
whether you're an established maintainer or entirely new to the project. It's very much
intended to be a collaborative one: It's not us telling you what we think is wrong with
your code, it's us working with you to produce something better together.

We have `a lengthy check list <guides/review.rst>`_ of things we look for in a review. Feel
free to have a read of it in advance and go through it yourself if you'd like to. It's not
required, but it might speed up the process.

Once your pull request has a green build and has passed review, it will be merged to
master fairly promptly. This will immediately trigger a release! Don't be scared. If that
breaks things, that's our fault not yours - the whole point of this process is to ensure
that problems get caught before we merge rather than after.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pull request or external package?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New strategies can be added to Hypothesis, or published as an external package
on PyPI - either is fine for most strategies.  If in doubt, ask!

It's generally much easier to get things working outside, because there's
more freedom to experiment and fewer requirements in stability and API style.
We're happy to review and help with external packages as well as pull requests;
several parts of Hypothesis started life outside and were integrated later
(with permission, of course).

To help people find your package, please use the `Framework :: Hypothesis
<https://pypi.org/search/?c=Framework+%3A%3A+Hypothesis>`__ `trove classifier
<https://pypi.org/classifiers/>`__.  We also recommend naming your package
in the pattern of ``hypothesis-graphql`` and ``hypothesis-protobuf`` on PyPI.

On the other hand, being inside gets you access to some deeper implementation
features (if you need them) and better long-term guarantees about maintenance.
We particularly encourage pull requests for new composable primitives that
make implementing other strategies easier, or for widely used types in the
Python standard library.  Strategies for other things are also welcome;
anything with external dependencies just goes in ``hypothesis.extra``.

~~~~~~~~~
The build
~~~~~~~~~

The build is driven by a ``build.sh`` shell script, which delegates to a custom Python-based build system.
Actually running the tests is managed by `tox <https://tox.readthedocs.io/en/latest/>`_, but the build system
will call out to the relevant tox environments so you mostly don't have to know anything about that
unless you want to make changes to the test config. You also mostly don't need to know anything about the build system
except to type ``./build.sh`` followed by the name of the task you want to run.

All of it will be checked on CI so you don't *have* to run anything locally, but you might
find it useful to do so: A full CI run can take up to twenty minutes,
so running a smaller set of tests locally can be helpful.

The build system should be "fairly" portable, but is currently only known to work on Linux or OS X. It *might* work
on a BSD or on Windows with cygwin installed, but it hasn't been tried.  Windows with WSL does work,
as for Linux, and since OS-specific issues are rare for Hypothesis that's pretty useful.
If you try it and find it doesn't work, please do submit patches to fix that.

Some notable commands:

``./build.sh check-coverage`` will verify 100% code coverage by running a
curated subset of the test suite.

``./build.sh check-py311`` (etc.) will run most of the test suite against a
particular python version.

``./build.sh format`` will reformat your code according to the Hypothesis coding style. You should use this before each
commit ideally, but you only really have to use it when you want your code to be ready to merge.

You can also use ``./build.sh check-format``, which will run format and some linting and will then error if you have a
git diff. Note: This will error even if you started with a git diff, so if you've got any uncommitted changes
this will necessarily report an error.

Run ``./build.sh tasks`` for a list of all supported build task names.

Note: The build requires a lot of different versions of python, so rather than have you install them yourself,
the build system will install them itself in a local directory. This means that the first time you run a task you
may have to wait a while as the build downloads and installs the right version of python for you.

~~~~~~~~~~~~~
Running Tests
~~~~~~~~~~~~~

The tasks described above will run all of the tests (e.g. ``check-py311``). But
the ``tox`` task will give finer-grained control over the test runner. At a
high level, the task takes the form:

.. code-block::

    ./build.sh tox py311-custom 3.11.3 [tox args] -- [pytest args]

Namely, first provide the tox environment (see ``tox.ini``), then the python
version to test with, then any ``tox`` or ``pytest`` args as needed. For
example, to run all of the tests in the file
``tests/nocover/test_conjecture_engine.py`` with python 3.12:

.. code-block::

    ./build.sh tox py312-custom 3.12.7 -- tests/nocover/test_conjecture_engine.py

See the ``tox`` docs and ``pytest`` docs for more information:
* https://docs.pytest.org/en/latest/how-to/usage.html
* https://tox.wiki/en/latest/config.html#cli

^^^^^^^^^^^
Test Layout
^^^^^^^^^^^

See ``hypothesis-python/tests/README.rst``

^^^^^^^^^^^^^^^^
Useful Arguments
^^^^^^^^^^^^^^^^

Some useful arguments to pytest include:

* You can pass ``-n 0`` to turn off ``pytest-xdist``'s parallel test execution.
  Sometimes for running just a small number of tests its startup time is longer
  than the time it saves (this will vary from system to system), so this can
  be helpful if you find yourself waiting on test runners to start a lot.
* You can use ``-k`` to select a subset of tests to run. This matches on substrings
  of the test names. For example ``-kfoo`` will only run tests that have "foo" as
  a substring of their name. You can also use composite expressions here.
  e.g. ``-k'foo and not bar'`` will run anything containing foo that doesn't
  also contain bar.  `More information on how to select tests to run can be found
  in the pytest documentation <https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests>`__.


