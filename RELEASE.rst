RELEASE_TYPE: minor

This release introduces two new features:

* pytest users can specify a seed to use for ``@given`` based tests by passing
  the ``--hypothesis-seed`` command line argument.
* When a test fails, either with a health check failure or a falsifying example,
  Hypothesis will print out a seed that led to that failure, if the test is not
  already running with a fixed seed. You can then recreate that failure using either
  the ``@seed`` decorator or (if you are running pytest) with ``--hypothesis-seed``.


This work was funded by `Smarkets <https://smarkets.com/>`_.
