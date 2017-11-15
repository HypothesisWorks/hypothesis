RELEASE_TYPE: minor

This release overhauls the health check system in a variety of small ways.
It adds no new features, but is nevertheless a minor release because it changes
which tests are likely to fail health checks.

The most noticeable effect is that some tests that used to fail health checks
will now pass, and some that used to pass will fail. These should all be
improvements in accuracy. In particular:

* New failures will usually be because they are now taking into account things
  like use of :func:`~hypothesis.strategies.data()` and
  :func:`~hypothesis.assume()` inside the test body.
* New failures *may* also be because for some classes of example the way data
  generation performance was measured was artificially faster than real data
  generation (for most examples that are hitting performance health checks the
  opposite should be the case).
* Tests that used to fail health checks and now pass do so because the health
  check system used to run in a way that was subtly different than the main
  Hypothesis data generation and lacked some of its support for e.g. large
  examples.

If your data generation is especially slow, you may also see your tests get
somewhat faster, as there is no longer a separate health check phase. This will
be particularly noticeable when rerunning test failures.

This work was funded by `Smarkets <https://smarkets.com/>`_.
