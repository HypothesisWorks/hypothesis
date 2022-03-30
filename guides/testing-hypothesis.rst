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

The ``hypothesis-python/tests/`` directory has some notes in the README file on where various
kinds of tests can be found or added.  Go there for the practical stuff, or
just ask one of the maintainers for help on a pull request!

Further reading: How `SQLite is tested <https://sqlite.org/testing.html>`_,
`how the Space Shuttle was tested <https://www.fastcompany.com/28121/they-write-right-stuff>`_,
`how to misuse code coverage <http://www.exampler.com/testing-com/writings/coverage.pdf>`_
(for inspiration, *not* implementation).
Dan Luu writes about `fuzz testing <https://danluu.com/testing/>`_ and
`broken processes <https://danluu.com/wat/>`_, among other things.

-------------
Running Tests
-------------

Tests are run via ``build.sh``. See ``CONTRIBUTING.rst`` for more details.
