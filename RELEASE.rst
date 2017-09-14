RELEASE_TYPE: minor

This release makes Hypothesis coverage aware. Hypothesis now runs all test
bodies under coverage, and uses this information to guide its testing.

The :attr:`~hypothesis.settings.use_coverage` setting can be used to disable
this behaviour if you want to test code that is sensitive to coverage being
enabled (either because of performance or interaction with the trace function).

The main benefits of this feature are:

* Hypothesis now observes when examples it discovers cover particular lines
  or branches and stores them in the database for later.
* Hypothesis will make some use of this information to guide its exploration of
  the search space and improve the examples it finds (this is currently used
  only very lightly and will likely improve significantly in future releases).

This also has the following side-effects:

* Hypothesis now has an install time dependency on the coverage package.
* Tests that are already running Hypothesis under coverage will likely get
  faster.
* Tests that are not running under coverage now run their test bodies under
  coverage by default (unless on pypy, where coverage is too slow for this to
  be a sensible default. You can still turn the feature on using the setting
  discussed below).
