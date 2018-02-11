==================
Testing Hypothesis
==================

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

We also use a variety of tools to check our code automatically.  This includes
formatting, import order, linting, and doctests (so examples in docs don't
break).  All of this is checked in CI - which means that once the build is
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
  pip install pytest-xdist flaky

Now whenever you want to run tests you can just activate the virtualenv
using ``source testing-venv/bin/activate`` or ``testing-venv\Scripts\activate``
and all of the dependencies will be available to you and your local copy
of Hypothesis will be on the path (so any edits will be picked up automatically
and you don't need to reinstall it in the local virtualenv).

-------------
Running Tests
-------------

To run a specific test file manually, you can use pytest. I usually use the
following invocation:

.. code-block::

    python -m pytest tests/cover/test_conjecture_engine.py

You will need to have Hypothesis installed locally to run these. I recommend a
virtualenv where you have run ``pip install -e .``, which installs all the
dependencies and puts your ``src`` directory in the path of installed packages
so that edits you make are automatically pipped up.

Useful arguments you can add to pytest are ``-n 0``, which will disable build
parallelism (I find that on my local laptop the startup time is too high to be
worth it when running single files, so I usually do this), and ``-kfoo`` where
foo is some substring common to the set of tests you want to run (you can also
use composite expressions here. e.g. ``-k'foo and not bar'`` will run anything
containing foo that doesn't also contain bar).
