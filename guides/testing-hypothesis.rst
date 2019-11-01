==================
Testing Hypothesis
==================

Note: This guide is currently entirely specific to the Python version of
Hypothesis.

This is a guide to the process of testing Hypothesis itself, both how to
run its tests and how to to write new ones.

--------------------------
General Testing Philosophy
--------------------------

The test suite for Hypothesis is unusually powerful - as you might hope! -
but the secret is actually more about attitude than technology.

The key is that we treat any bug in Hypothesis as a bug in our test suite
too - and think about the kinds of bugs that might not be caught, then write
tests that would catch them.

We also use a variety of tools to check our code automatically, including
formatting, import order, linting, and typing our API with Mypy.
All of this is checked in CI - which means that once the build is
green, humans can all focus on meaningful review rather than nitpicking
operator spacing.

Similarly, we require all code to have tests with 100% branch coverage - as
a starting point, not the final goal.

- Requiring full coverage can't guarantee that we've written all the tests
  worth writing (for example, maybe we left off a useful assertion about the
  result), but less than full coverage guarantees that there's some code we're
  not testing at all.
- Tests beyond full coverage generally aim to demonstrate that a particular
  feature works, or that some subtle failure case is not present - often
  because when it was found and fixed, someone wrote a test to make sure it
  couldn't come back!

The ``tests/`` directory has some notes in the README file on where various
kinds of tests can be found or added.  Go there for the practical stuff, or
just ask one of the maintainers for help on a pull request!

Further reading: How `SQLite is tested <https://sqlite.org/testing.html>`_,
`how the Space Shuttle was tested <https://www.fastcompany.com/28121/they-write-right-stuff>`_,
`how to misuse code coverage <http://www.exampler.com/testing-com/writings/coverage.pdf>`_
(for inspiration, *not* implementation).
Dan Luu writes about `fuzz testing <https://danluu.com/testing/>`_ and
`broken processes <https://danluu.com/wat/>`_, among other things.

---------------------------------------
Setting up a virtualenv to run tests in
---------------------------------------

If you want to run individual tests rather than relying on the make tasks
(which you probably will), it's easiest to do this in a virtualenv.

The following will give you a working virtualenv for running tests in:

.. code-block:: bash

  pip install virtualenv
  python -m virtualenv testing-venv

  # On Windows: testing-venv\Scripts\activate
  source testing-venv/bin/activate

  # Can also use pip install -e .[all] to get
  # all optional dependencies
  pip install -e .

  # Test specific dependencies.
  pip install pytest-xdist flaky mock pexpect

Now whenever you want to run tests you can just activate the virtualenv
using ``source testing-venv/bin/activate`` or ``testing-venv\Scripts\activate``
and all of the dependencies will be available to you and your local copy
of Hypothesis will be on the path (so any edits will be picked up automatically
and you don't need to reinstall it in the local virtualenv).

-------------
Running Tests
-------------

In order to run tests outside of the make/tox/etc set up, you'll need an
environment where Hypothesis is on the path and all of the testing dependencies
are installed.
We recommend doing this inside a virtualenv as described in the previous section.

All testing is done using `pytest <https://docs.pytest.org/en/latest/>`_,
with a couple of plugins installed. For advanced usage we recommend reading the
pytest documentation, but this section will give you a primer in enough of the
common commands and arguments to get started.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Selecting Which Files to Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following invocation runs all of the tests in the file
`tests/cover/test_conjecture_engine.py`:

.. code-block::

    python -m pytest tests/cover/test_conjecture_engine.py

If you want to run multiple files you can pass them all as arguments, and if
you pass a directory then it will run all files in that directory.
For example the following runs all the files in `test_conjecture_engine.py`
and `test_slippage.py`

.. code-block::

    python -m pytest tests/cover/test_conjecture_engine.py tests/cover/test_slippage.py

If you were running this in bash (if you're not sure: if you're not on Windows
you probably are) you could also use the syntax:

.. code-block::

    python -m pytest tests/cover/test_{conjecture_engine,slippage}.py

And the following would run all tests under `tests/cover`:

.. code-block::

    python -m pytest tests/cover


~~~~~~~~~~~
Test Layout
~~~~~~~~~~~

The top level structure of the tests in Hypothesis looks as follows:

* ``cover`` contains tests that we measure coverage for. This is intended to
  be a fairly minimal and fast set of tests that still gives pretty good
  confidence in the behaviour of the test suite. It is currently failing at
  both "minimal" and "fast", but we're trying to move it back in that
  direction. Try not to add tests to this unless they're actually to cover
  some specific target.
* ``nocover`` is a general dumping ground for slower tests that aren't needed
  to achieve coverage.
* ``quality`` is for expensive tests about the distribution or shrinking of
  examples. These will only be run on one Python version.
* ``py2`` and ``py3`` are for tests which only run on one major version of
  Python. You can also write these in other directories using
  ``pytest.mark.skipif``, but these directories are useful for things that
  require a version-specific syntax.
* The remaining test directories are for testing specific extras modules and
  should have the same name.

As a rule of thumb when writing new tests, they should go in nocover unless
they are for a specific extras module or to deliberately target a particular
line for coverage. In the latter case, prefer fast unit tests over larger and
slower integration tests (we are not currently very good at this).


~~~~~~~~~~~~~~~~
Useful Arguments
~~~~~~~~~~~~~~~~

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
