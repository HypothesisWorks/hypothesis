===========
Don't Panic
===========

The Hypothesis test suite is large, but we've written these notes to help you
out.  It's aimed at contributors (new and old!) who know they need to add tests
*somewhere*, but aren't sure where - or maybe need some hints on what kinds of
tests might be useful.  Others might just be interested in how a testing
library tests itself!


The very short version
======================

- To improve code coverage (eg because ``make check-coverage`` or CI is failing),
  go to ``cover/``
- For longer / system / integration tests, look in ``nocover/``
- For tests that require an optional dependency, look in the directory
  named for that dependency.

.. note::
    If you get stuck, just ask a maintainer to help out by mentioning
    ``@HypothesisWorks/hypothesis-python-contributors`` on GitHub.
    We'd love to help - and also get feedback on how this document could
    be better!


Some scenarios
==============

**I'm adding or changing a strategy**
    Check for a file specific to that strategy (eg ``test_uuids.py`` for
    the ``uuids()`` strategy).  Write tests for all invalid argument handling
    in ``test_direct_strategies.py``.  Strategies with optional dependencies
    should go in ``hypothesis.extras``, and the tests in their own module
    (ie not in ``cover``).  When you think you might be done, push and let
    our CI system point out any failing tests or non-covered code!

**I've made some internal changes**
    That's not very specific - you should probably refer to the test-finding
    tips in the next section.  Remember that ``tests/cover`` is reasonably
    quick unit-test style tests - you should consider writing more intensive
    integration tests too, but put them in ``tests/nocover`` with the others.


Finding particular tests
========================

With the sheer size and variety in this directory finding a specific thing
can be tricky.  Tips:

- Check for filenames that are relevant to your contribution.
- Use ``git grep`` to search for keywords, e.g. the name of a strategy you've changed.
- Deliberately break something related to your code, and see which tests fail.
- Ask a maintainer!  Sometimes the structure is just arbitrary, and other tactics
  don't work - but we *want* to help!


About each group of tests
=========================

Still here?  Here's a note on what to expect in each directory.

``common/``
    Useful shared testing code, including test setup and a few helper
    functions in ``utils.py``.  Also read up on
    `pytest <https://docs.pytest.org/en/latest/contents.html>`_
    features such as ``mark.parametrize``, ``mark.skipif``, and ``raises``
    for other functions that are often useful when writing tests.

``conjecture/``
    As for ``cover/``, but specific to ``hypothesis.internal.conjecture``.

``cover/``
    The home of enough tests to get 100% branch coverage, as quickly as possible
    without compromising on test power.  This can be an intimidating target,
    but it's entirely achievable and the maintainers are (still) here to help.

    This directory alone has around two-thirds of the tests for Hypothesis
    (~8k of ~12k lines of code).  If you're adding or fixing tests, chances
    are therefore good that they're in here!

``datetime/``
    Tests which depend on the ``pytz`` or ``dateutil`` packages for timezones.

``django/``
    Tests for the Django extra.  Includes a toy application, to give us lots
    of models to generate.

``lark/``
    Tests for the Lark extra for context-free grammars, which depend on the
    ``lark`` package.

``nocover/``
    More expensive and longer-running tests, typically used to test trickier
    interactions or check for regressions in expensive bugs.  Lots of tests
    about how values shrink, databases, compatibility, etc.

    New tests that are not required for full coverage of code branches or
    behaviour should also go in ``nocover``, to keep ``cover`` reasonably fast.

``numpy/``
    Tests for the Numpy extra.

``pandas/``
    Tests for the Pandas extra.

``pytest/``
    Hypothesis has excellent integration with ``pytest``, though we are careful
    to support other test runners including unittest and nose.  This is where we
    test that our pytest integration is working properly.

``quality/``
    Tests that various hard-to-find examples do in fact get found by Hypothesis,
    as well as some stuff about example shrinking.  Mostly intended for tests
    of the form "Hypothesis finds an example of this condition" + assertions
    about which example it finds.
