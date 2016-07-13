=========
Changelog
=========

This is a record of all past Hypothesis releases and what went into them,
in reverse chronological order. All previous releases should still be available
on pip.

Hypothesis APIs come in three flavours:

* Public: Hypothesis releases since 1.0 are `semantically versioned <http://semver.org/>`_
  with respect to these parts of the API. These will not break except between
  major version bumps. All APIs mentioned in this documentation are public unless
  explicitly noted otherwise.
* Semi-public: These are APIs that are considered ready to use but are not wholly
  nailed down yet. They will not break in patch releases and will *usually* not break
  in minor releases, but when necessary  minor releases may break semi-public APIs.
* Internal: These may break at any time and you really should not use them at
  all.

You should generally assume that an API is internal unless you have specific
information to the contrary.


------------------
3.4.2 - 2016-07-13
------------------

This is a bug fix release, fixing a number of problems with the settings system:

* Test functions defined using @given can now be called from other threads
  (Issue #337)
* Attempting to delete a settings property would previously have silently done
  the wrong thing. Now it raises an AttributeError.
* Creating a settings object with a custom database_file parameter was silently
  getting ignored and the default was being used instead. Now it's not.

------------------
3.4.1 - 2016-07-07
------------------

This is a bug fix release for a single bug:

* On Windows when running two Hypothesis processes in parallel (e.g. using
  pytest-xdist) they could race with each other and one would raise an exception
  due to the non-atomic nature of file renaming on Windows and the fact that you
  can't rename over an existing file. This is now fixed.

------------------
3.4.0 - 2016-05-27
------------------

This release is entirely provided by `Lucas Wiman <https://github.com/lucaswiman>`_:

models() strategies from hypothesis.extra.django will now respect much more of
Django's validations out of the box. Wherever possible full_clean() should
succeed.

In particular:

* The max_length, blank and choices kwargs are now respected.
* Add support for DecimalField.
* If a field includes validators, the list of validators are used to filter the field strategy.

------------------
3.3.0 - 2016-05-27
------------------

This release went wrong and is functionally equivalent to 3.2.0. Ignore it.

------------------
3.2.0 - 2016-05-19
------------------

This is a small single-feature release:

* All tests using @given now fix the global random seed. This removes the health
  check for that. If a non-zero seed is required for the final falsifying
  example, it will be reported. Otherwise Hypothesis will assume randomization
  was not a significant factor for the test and be silent on the subject. If you
  use the random_module() strategy this will continue to work and will always
  display the seed.

------------------
3.1.3 - 2016-05-01
------------------

Single bug fix release

* Another charmap problem. In 3.1.2 text/characters would break on systems
  which had /tmp/ mounted on a different partition than the Hypothesis storage
  directory (usually in home). This fixes that.

------------------
3.1.2 - 2016-04-30
------------------

Single bug fix release:

* Anything which used a text() or characters() strategy was broken on Windows
  and I hadn't updated appveyor to use the new repository location so I didn't
  notice. This is now fixed and windows support should work correctly.

------------------
3.1.1 - 2016-04-29
------------------

Minor bug fix release.

* Fix concurrency issue when running tests that use text() from multiple
  processes at once (Bug #302, thanks to Alex Chan).
* Improve performance of code using lists with max_size (thanks to
  Cristi Cobzarenco).
* Fix install on Python 2 with ancient versions of pip so that it installs the
  enum34 backport (thanks to Donald Stufft for telling me how to do this).
* Remove duplicated __all__ exports from hypothesis.strategies (thanks to
  Piët Delport).
* Update headers to point to new repository location.
* Allow use of strategies that can't be used in find() (e.g. choices) in
  stateful testing.


------------------
3.1.0 - 2016-03-06
------------------

* Add a 'nothing' strategy that never successfully generates values.
* sampled_from() and one_of() can both now be called with an empty argument
  list, in which case they also never generate any values.
* one_of may now be called with a single argument that is a collection of strategies
  as well as as varargs.
* Add a 'runner' strategy which returns the instance of the current test object
  if there is one.
* 'Bundle' for RuleBasedStateMachine is now a normal(ish) strategy and can be used
  as such.
* Tests using RuleBasedStateMachine should now shrink significantly better.
* Hypothesis now uses a pretty-printing library internally, compatible with IPython's
  pretty printing protocol (actually using the same code). This may improve the quality
  of output in some cases.
* As a 'phases' setting that allows more fine grained control over which parts of the
  process Hypothesis runs
* Add a suppress_health_check setting which allows you to turn off specific health checks
  in a fine grained manner.
* Fix a bug where lists of non fixed size would always draw one more element than they
  included. This mostly didn't matter, but if would cause problems with empty strategies
  or ones with side effects.
* Add a mechanism to the Django model generator to allow you to explicitly request the
  default value (thanks to Jeremy Thurgood for this one).

------------------
3.0.5 - 2016-02-25
------------------

* Fix a bug where Hypothesis would now error on py.test development versions.

------------------
3.0.4 - 2016-02-24
------------------

* Fix a bug where Hypothesis would error when running on Python 2.7.3 or
  earlier because it was trying to pass a bytearray object to struct.unpack (
  which is only supported since 2.7.4).

------------------
3.0.3 - 2016-02-23
------------------

* Fix version parsing of py.test to work with py.test release candidates
* More general handling of the health check problem where things could fail because
  of a cache miss - now one "free" example is generated before the start of the
  health check run.

------------------
3.0.2 - 2016-02-18
------------------

* Under certain circumstances, strategies involving text() buried inside some
  other strategy (e.g. text().filter(...) or recursive(text(), ...)) would cause
  a test to fail its health checks the first time it ran. This was caused by having
  to compute some related data and cache it to disk. On travis or anywhere else
  where the .hypothesis directory was recreated this would have caused the tests
  to fail their health check on every run. This is now fixed for all the known cases,
  although there could be others lurking.

------------------
3.0.1 - 2016-02-18
------------------

* Fix a case where it was possible to trigger an "Unreachable" assertion when
  running certain flaky stateful tests.
* Improve shrinking of large stateful tests by eliminating a case where it was
  hard to delete early steps.
* Improve efficiency of drawing binary(min_size=n, max_size=n) significantly by
  provide a custom implementation for fixed size blocks that can bypass a lot
  of machinery.
* Set default home directory based on the current working directory at the
  point Hypothesis is imported, not whenever the function first happens to be
  called.

------------------
3.0.0 - 2016-02-17
------------------

Codename: This really should have been 2.1.

Externally this looks like a very small release. It has one small breaking change
that probably doesn't affect anyone at all (some behaviour that never really worked
correctly is now outright forbidden) but necessitated a major version bump and one
visible new feature.

Internally this is a complete rewrite. Almost nothing other than the public API is
the same.

New features:

* Addition of data() strategy which allows you to draw arbitrary data interactively
  within the test.
* New "exploded" database format which allows you to more easily check the example
  database into a source repository while supporting merging.
* Better management of how examples are saved in the database.
* Health checks will now raise as errors when they fail. It was too easy to have
  the warnings be swallowed entirely.

New limitations:

* choices and streaming strategies may no longer be used with find(). Neither may
  data() (this is the change that necessitated a major version bump).

Feature removal:

* The ForkingTestCase executor has gone away. It may return in some more working
  form at a later date.

Performance improvements:

* A new model which allows flatmap, composite strategies and stateful testing to
  perform *much* better. They should also be more reliable.
* Filtering may in some circumstances have improved significantly. This will
  help especially in cases where you have lots of values with individual filters
  on them, such as lists(x.filter(...)).
* Modest performance improvements to the general test runner by avoiding expensive
  operations

In general your tests should have got faster. If they've instead got significantly
slower, I'm interested in hearing about it.

Data distribution:

The data distribution should have changed significantly. This may uncover bugs the
previous version missed. It may also miss bugs the previous version could have
uncovered. Hypothesis is now producing less strongly correlated data than it used
to, but the correlations are extended over more of the structure.

Shrinking:

Shrinking quality should have improved. In particular Hypothesis can now perform
simultaneous shrinking of separate examples within a single test (previously it
was only able to do this for elements of a single collection). In some cases
performance will have improved, in some cases it will have got worse but generally
shouldn't have by much.

------------------
2.0.0 - 2016-01-10
------------------

Codename: A new beginning

This release cleans up all of the legacy that accrued in the course of
Hypothesis 1.0. These are mostly things that were emitting deprecation warnings
in 1.19.0, but there were a few additional changes.

In particular:

* non-strategy values will no longer be converted to strategies when used in
  given or find.
* FailedHealthCheck is now an error and not a warning.
* Handling of non-ascii reprs in user types have been simplified by using raw
  strings in more places in Python 2.
* given no longer allows mixing positional and keyword arguments.
* given no longer works with functions with defaults.
* given no longer turns provided arguments into defaults - they will not appear
  in the argspec at all.
* the basic() strategy no longer exists.
* the n_ary_tree strategy no longer exists.
* the average_list_length setting no longer exists. Note: If you're using
  using recursive() this will cause you a significant slow down. You should
  pass explicit average_size parameters to collections in recursive calls.
* @rule can no longer be applied to the same method twice.
* Python 2.6 and 3.3 are no longer officially supported, although in practice
  they still work fine.

This also includes two non-deprecation changes:

* given's keyword arguments no longer have to be the rightmost arguments and
  can appear anywhere in the method signature.
* The max_shrinks setting would sometimes not have been respected.


-------------------
1.19.0 - 2016-01-09
-------------------

Codename: IT COMES

This release heralds the beginning of a new and terrible age of Hypothesis 2.0.

It's primary purpose is some final deprecations prior to said release. The goal
is that if your code emits no warnings under this release then it will probably run
unchanged under Hypothesis 2.0 (there are some caveats to this: 2.0 will drop
support for some Python versions, and if you're using internal APIs then as usual
that may break without warning).

It does have two new features:

* New @seed() decorator which allows you to manually seed a test. This may be
  harmlessly combined with and overrides the derandomize setting.
* settings objects may now be used as a decorator to fix those settings to a
  particular @given test.

API changes (old usage still works but is deprecated):

* Settings has been renamed to settings (lower casing) in order to make the
  decorator usage more natural.
* Functions for the storage directory that were in hypothesis.settings are now
  in a new hypothesis.configuration module.

Additional deprecations:

* the average_list_length setting has been deprecated in favour of being
  explicit.
* the basic() strategy has been deprecated as it is impossible to support
  it under a Conjecture based model, which will hopefully be implemented at
  some point in the 2.x series.
* the n_ary_tree strategy (which was never actually part of the public API)
  has been deprecated.
* Passing settings or random as keyword arguments to given is deprecated (use
  the new functionality instead)


Bug fixes:

* No longer emit PendingDeprecationWarning for __iter__ and StopIteration in
  streaming() values.
* When running in health check mode with non strict, don't print quite so
  many errors for an exception in reify.
* When an assumption made in a test or a filter is flaky, tests will now
  raise Flaky instead of UnsatisfiedAssumption.


-----------------------------------------------------------------------
`1.18.1 <https://hypothesis.readthedocs.io/en/1.18.0/>`_ - 2015-12-22
-----------------------------------------------------------------------

Two behind the scenes changes:

* Hypothesis will no longer write generated code to the file system. This
  will improve performance on some systems (e.g. if you're using
  `PythonAnywhere <https://www.pythonanywhere.com/>`_ which is running your
  code from NFS) and prevent some annoying interactions with auto-restarting
  systems.
* Hypothesis will cache the creation of some strategies. This can significantly
  improve performance for code that uses flatmap or composite and thus has to
  instantiate strategies a lot.

-----------------------------------------------------------------------
`1.18.0 <https://hypothesis.readthedocs.io/en/1.18.0/>`_ - 2015-12-21
-----------------------------------------------------------------------

Features:

* Tests and find are now explicitly seeded off the global random module. This
  means that if you nest one inside the other you will now get a health check
  error. It also means that you can control global randomization by seeding
  random.
* There is a new random_module() strategy which seeds the global random module
  for you and handles things so that you don't get a health check warning if
  you use it inside your tests.
* floats() now accepts two new arguments: allow_nan and allow_infinity. These
  default to the old behaviour, but when set to False will do what the names
  suggest.

Bug fixes:

* Fix a bug where tests that used text() on Python 3.4+ would not actually be
  deterministic even when explicitly seeded or using the derandomize mode,
  because generation depended on dictionary iteration order which was affected
  by hash randomization.
* Fix a bug where with complicated strategies the timing of the initial health
  check could affect the seeding of the subsequent test, which would also
  render supposedly deterministic tests non-deterministic in some scenarios.
* In some circumstances flatmap() could get confused by two structurally
  similar things it could generate and would produce a flaky test where the
  first time it produced an error but the second time it produced the other
  value, which was not an error. The same bug was presumably also possible in
  composite().
* flatmap() and composite() initial generation should now be moderately faster.
  This will be particularly noticeable when you have many values drawn from the
  same strategy in a single run, e.g. constructs like lists(s.flatmap(f)).
  Shrinking performance *may* have suffered, but this didn't actually produce
  an interestingly worse result in any of the standard scenarios tested.

-----------------------------------------------------------------------
`1.17.1 <https://hypothesis.readthedocs.io/en/1.17.1/>`_ - 2015-12-16
-----------------------------------------------------------------------

A small bug fix release, which fixes the fact that the 'note' function could
not be used on tests which used the @example decorator to provide explicit
examples.

-----------------------------------------------------------------------
`1.17.0 <https://hypothesis.readthedocs.io/en/1.17.0/>`_ - 2015-12-15
-----------------------------------------------------------------------

This is actually the same release as 1.16.1, but 1.16.1 has been pulled because
it contains the following additional change that was not intended to be in a
patch  release (it's perfectly stable, but is a larger change that should have
required a minor version bump):

* Hypothesis will now perform a series of "health checks" as part of running
  your tests. These detect and warn about some common error conditions that
  people often run into which wouldn't necessarily have caued the test to fail
  but would cause e.g. degraded performance or confusing results.

-----------------------------------------------------------------------
`1.16.1 <https://hypothesis.readthedocs.io/en/1.16.1/>`_ - 2015-12-14
-----------------------------------------------------------------------

Note: This release has been removed.

A small bugfix release that allows bdists for Hypothesis to be built
under 2.7 - the compat3.py file which had Python 3 syntax wasn't intended
to be loaded under Python 2, but when building a bdist it was. In particular
this would break running setup.py test.

-----------------------------------------------------------------------
`1.16.0 <https://hypothesis.readthedocs.io/en/1.16.0/>`_ - 2015-12-08
-----------------------------------------------------------------------

There are no public API changes in this release but it includes a behaviour
change that I wasn't comfortable putting in a patch release.

* Functions from hypothesis.strategies will no longer raise InvalidArgument
  on bad arguments. Instead the same errors will be raised when a test
  using such a strategy is run. This may improve startup time in some
  cases, but the main reason for it is so that errors in strategies
  won't cause errors in loading, and it can interact correctly with things
  like pytest.mark.skipif.
* Errors caused by accidentally invoking the legacy API are now much less
  confusing, although still throw NotImplementedError.
* hypothesis.extra.django is 1.9 compatible.
* When tests are run with max_shrinks=0 this will now still rerun the test
  on failure and will no longer print "Trying example:" before each run.
  Additionally note() will now work correctly when used with max_shrinks=0.

-----------------------------------------------------------------------
`1.15.0 <https://hypothesis.readthedocs.io/en/1.15.0/>`_ - 2015-11-24
-----------------------------------------------------------------------

A release with two new features.

* A 'characters' strategy for more flexible generation of text with particular
  character ranges and types, kindly contributed by `Alexander Shorin <https://github.com/kxepal>`_.
* Add support for preconditions to the rule based stateful testing. Kindly
  contributed by `Christopher Armstrong <https://github.com/radix>`_


-----------------------------------------------------------------------
`1.14.0 <https://hypothesis.readthedocs.io/en/1.14.0/>`_ - 2015-11-01
-----------------------------------------------------------------------


New features:

* Add 'note' function which lets you include additional information in the
  final test run's output.
* Add 'choices' strategy which gives you a choice function that emulates
  random.choice.
* Add 'uuid' strategy that generates UUIDs'
* Add 'shared' strategy that lets you create a strategy that just generates a
  single shared value for each test run

Bugs:

* Using strategies of the form streaming(x.flatmap(f)) with find or in stateful
  testing would have caused InvalidArgument errors when the resulting values
  were used (because code that expected to only be called within a test context
  would be invoked).


-----------------------------------------------------------------------
`1.13.0 <https://hypothesis.readthedocs.io/en/1.13.0/>`_ - 2015-10-29
-----------------------------------------------------------------------

This is quite a small release, but deprecates some public API functions
and removes some internal API functionality so gets a minor version bump.

* All calls to the 'strategy' function are now deprecated, even ones which
  pass just a SearchStrategy instance (which is still a no-op).
* Never documented hypothesis.extra entry_points mechanism has now been removed (
  it was previously how hypothesis.extra packages were loaded and has been deprecated
  and unused for some time)
* Some corner cases that could previously have produced an OverflowError when simplifying
  failing cases using hypothesis.extra.datetimes (or dates or times) have now been fixed.
* Hypothesis load time for first import has been significantly reduced - it used to be
  around 250ms (on my SSD laptop) and now is around 100-150ms. This almost never
  matters but was slightly annoying when using it in the console.
* hypothesis.strategies.randoms was previously missing from \_\_all\_\_.

-----------------------------------------------------------------------
`1.12.0 <https://hypothesis.readthedocs.io/en/1.12.0/>`_ - 2015-10-18
-----------------------------------------------------------------------

* Significantly improved performance of creating strategies using the functions
  from the hypothesis.strategies module by deferring the calculation of their
  repr until it was needed. This is unlikely to have been an performance issue
  for you unless you were using flatmap, composite or stateful testing, but for
  some cases it could be quite a significant impact.
* A number of cases where the repr of strategies build from lambdas is improved
* Add dates() and times() strategies to hypothesis.extra.datetimes
* Add new 'profiles' mechanism to the settings system
* Deprecates mutability of Settings, both the Settings.default top level property
  and individual settings.
* A Settings object may now be directly initialized from a parent Settings.
* @given should now give a better error message if you attempt to use it with a
  function that uses destructuring arguments (it still won't work, but it will
  error more clearly),
* A number of spelling corrections in error messages
* py.test should no longer display the intermediate modules Hypothesis generates
  when running in verbose mode
* Hypothesis should now correctly handle printing objects with non-ascii reprs
  on python 3 when running in a locale that cannot handle ascii printing to
  stdout.
* Add a unique=True argument to lists(). This is equivalent to
  unique_by=lambda x: x, but offers a more convenient syntax.


-----------------------------------------------------------------------
`1.11.4 <https://hypothesis.readthedocs.io/en/1.11.4/>`_ - 2015-09-27
-----------------------------------------------------------------------

* Hide modifications Hypothesis needs to make to sys.path by undoing them
  after we've imported the relevant modules. This is a workaround for issues
  cryptography experienced on windows.
* Slightly improved performance of drawing from sampled_from on large lists
  of alternatives.
* Significantly improved performance of drawing from one_of or strategies
  using \| (note this includes a lot of strategies internally - floats()
  and integers() both fall into this category). There turned out to be a
  massive performance regression introduced in 1.10.0 affecting these which
  probably would have made tests using Hypothesis significantly slower than
  they should have been.

-----------------------------------------------------------------------
`1.11.3 <https://hypothesis.readthedocs.io/en/1.11.3/>`_ - 2015-09-23
-----------------------------------------------------------------------

* Better argument validation for datetimes() strategy - previously setting
  max_year < datetime.MIN_YEAR or min_year > datetime.MAX_YEAR would not have
  raised an InvalidArgument error and instead would have behaved confusingly.
* Compatibility with being run on pytest < 2.7 (achieved by disabling the
  plugin).

-----------------------------------------------------------------------
`1.11.2 <https://hypothesis.readthedocs.io/en/1.11.2/>`_ - 2015-09-23
-----------------------------------------------------------------------

Bug fixes:

* Settings(database=my_db) would not be correctly inherited when used as a
  default setting, so that newly created settings would use the database_file
  setting and create an SQLite example database.
* Settings.default.database = my_db would previously have raised an error and
  now works.
* Timeout could sometimes be significantly exceeded if during simplification
  there were a lot of examples tried that didn't trigger the bug.
* When loading a heavily simplified example using a basic() strategy from the
  database this could cause Python to trigger a recursion error.
* Remove use of deprecated API in pytest plugin so as to not emit warning

Misc:

* hypothesis-pytest is now part of hypothesis core. This should have no
  externally visible consequences, but you should update your dependencies to
  remove hypothesis-pytest and depend on only Hypothesis.
* Better repr for hypothesis.extra.datetimes() strategies.
* Add .close() method to abstract base class for Backend (it was already present
  in the main implementation).

-----------------------------------------------------------------------
`1.11.1 <https://hypothesis.readthedocs.io/en/1.11.1/>`_ - 2015-09-16
-----------------------------------------------------------------------

Bug fixes:

* When running Hypothesis tests in parallel (e.g. using pytest-xdist) there was a race
  condition caused by code generation.
* Example databases are now cached per thread so as to not use sqlite connections from
  multiple threads. This should make Hypothesis now entirely thread safe.
* floats() with only min_value or max_value set would have had a very bad distribution.
* Running on 3.5, Hypothesis would have emitted deprecation warnings because of use of
  inspect.getargspec

-----------------------------------------------------------------------
`1.11.0 <https://hypothesis.readthedocs.io/en/1.11.0/>`_ - 2015-08-31
-----------------------------------------------------------------------

* text() with a non-string alphabet would have used the repr() of the the alphabet
  instead of its contexts. This is obviously silly. It now works with any sequence
  of things convertible to unicode strings.
* @given will now work on methods whose definitions contains no explicit positional
  arguments, only varargs (`bug #118 <https://github.com/HypothesisWorks/hypothesis-python/issues/118>`_).
  This may have some knock on effects because it means that @given no longer changes the
  argspec of functions other than by adding defaults.
* Introduction of new @composite feature for more natural definition of strategies you'd
  previously have used flatmap for.

-----------------------------------------------------------------------
`1.10.6 <https://hypothesis.readthedocs.io/en/1.10.6/>`_ - 2015-08-26
-----------------------------------------------------------------------

Fix support for fixtures on Django 1.7.

-----------------------------------------------------------------------
`1.10.4 <https://hypothesis.readthedocs.io/en/1.10.4/>`_ - 2015-08-21
-----------------------------------------------------------------------

Tiny bug fix release:

* If the database_file setting is set to None, this would have resulted in
  an error when running tests. Now it does the same as setting database to
  None.

-----------------------------------------------------------------------
`1.10.3 <https://hypothesis.readthedocs.io/en/1.10.3/>`_ - 2015-08-19
-----------------------------------------------------------------------

Another small bug fix release.

* lists(elements, unique_by=some_function, min_size=n) would have raised a
  ValidationError if n > Settings.default.average_list_length because it would
  have wanted to use an average list length shorter than the minimum size of
  the list, which is impossible. Now it instead defaults to twice the minimum
  size in these circumstances.
* basic() strategy would have only ever produced at most ten distinct values
  per run of the test (which is bad if you e.g. have it inside a list). This
  was obviously silly. It will now produce a much better distribution of data,
  both duplicated and non duplicated.


-----------------------------------------------------------------------
`1.10.2 <https://hypothesis.readthedocs.io/en/1.10.2/>`_ - 2015-08-19
-----------------------------------------------------------------------

This is a small bug fix release:

* star imports from hypothesis should now work correctly.
* example quality for examples using flatmap will be better, as the way it had
  previously been implemented was causing problems where Hypothesis was
  erroneously labelling some examples as being duplicates.

-----------------------------------------------------------------------
`1.10.0 <https://hypothesis.readthedocs.io/en/1.10.0/>`_ - 2015-08-04
-----------------------------------------------------------------------

This is just a bugfix and performance release, but it changes some
semi-public APIs, hence the minor version bump.

* Significant performance improvements for strategies which are one\_of()
  many branches. In particular this included recursive() strategies. This
  should take the case where you use one recursive() strategy as the base
  strategy of another from unusably slow (tens of seconds per generated
  example) to reasonably fast.
* Better handling of just() and sampled_from() for values which have an
  incorrect \_\_repr\_\_ implementation that returns non-ASCII unicode
  on Python 2.
* Better performance for flatmap from changing the internal morpher API
  to be significantly less general purpose.
* Introduce a new semi-public BuildContext/cleanup API. This allows
  strategies to register cleanup activities that should run once the
  example is complete. Note that this will interact somewhat weirdly with
  find.
* Better simplification behaviour for streaming strategies.
* Don't error on lambdas which use destructuring arguments in Python 2.
* Add some better reprs for a few strategies that were missing good ones.
* The Random instances provided by randoms() are now copyable.
* Slightly more debugging information about simplify when using a debug
  verbosity level.
* Support using given for functions with varargs, but not passing arguments
  to it as positional.

---------------------------------------------------------------------
`1.9.0 <https://hypothesis.readthedocs.io/en/1.9.0/>`_ - 2015-07-27
---------------------------------------------------------------------

Codename: The great bundling.

This release contains two fairly major changes.

The first is the deprecation of the hypothesis-extra mechanism. From
now on all the packages that were previously bundled under it other
than hypothesis-pytest (which is a different beast and will remain
separate). The functionality remains unchanged and you can still import
them from exactly the same location, they just are no longer separate
packages.

The second is that this introduces a new way of building strategies
which lets you build up strategies recursively from other strategies.

It also contains the minor change that calling .example() on a
strategy object will give you examples that are more representative of
the actual data you'll get. There used to be some logic in there to make
the examples artificially simple but this proved to be a bad idea.

---------------------------------------------------------------------
`1.8.5 <https://hypothesis.readthedocs.io/en/1.8.5/>`_ - 2015-07-24
---------------------------------------------------------------------

This contains no functionality changes but fixes a mistake made with
building the previous package that would have broken installation on
Windows.

---------------------------------------------------------------------
`1.8.4 <https://hypothesis.readthedocs.io/en/1.8.4/>`_ - 2015-07-20
---------------------------------------------------------------------

Bugs fixed:

* When a call to floats() had endpoints which were not floats but merely
  convertible to one (e.g. integers), these would be included in the generated
  data which would cause it to generate non-floats.
* Splitting lambdas used in the definition of flatmap, map or filter over
  multiple lines would break the repr, which would in turn break their usage.


---------------------------------------------------------------------
`1.8.3 <https://hypothesis.readthedocs.io/en/1.8.3/>`_ - 2015-07-20
---------------------------------------------------------------------

"Falsifying example" would not have been printed when the failure came from an
explicit example.

---------------------------------------------------------------------
`1.8.2 <https://hypothesis.readthedocs.io/en/1.8.2/>`_ - 2015-07-18
---------------------------------------------------------------------

Another small bugfix release:

* When using ForkingTestCase you would usually not get the falsifying example
  printed if the process exited abnormally (e.g. due to os._exit).
* Improvements to the distribution of characters when using text() with a
  default alphabet. In particular produces a better distribution of ascii and
  whitespace in the alphabet.

---------------------------------------------------------------------
`1.8.1 <https://hypothesis.readthedocs.io/en/1.8.1/>`_ - 2015-07-17
---------------------------------------------------------------------

This is a small release that contains a workaround for people who have
bad reprs returning non ascii text on Python 2.7. This is not a bug fix
for Hypothesis per se because that's not a thing that is actually supposed
to work, but Hypothesis leans more heavily on repr than is typical so it's
worth having a workaround for.

---------------------------------------------------------------------
`1.8.0 <https://hypothesis.readthedocs.io/en/1.8.0/>`_ - 2015-07-16
---------------------------------------------------------------------

New features:

* Much more sensible reprs for strategies, especially ones that come from
  hypothesis.strategies. These should now have as reprs python code that 
  would produce the same strategy.
* lists() accepts a unique_by argument which forces the generated lists to be
  only contain elements unique according to some function key (which must
  return a hashable value).
* Better error messages from flaky tests to help you debug things.

Mostly invisible implementation details that may result in finding new bugs
in your code:

* Sets and dictionary generation should now produce a better range of results.
* floats with bounds now focus more on 'critical values', trying to produce
  values at edge cases.
* flatmap should now have better simplification for complicated cases, as well
  as generally being (I hope) more reliable.

Bug fixes:

* You could not previously use assume() if you were using the forking executor.


---------------------------------------------------------------------
`1.7.2 <https://hypothesis.readthedocs.io/en/1.7.2/>`_ - 2015-07-10
---------------------------------------------------------------------

This is purely a bug fix release:

* When using floats() with stale data in the database you could sometimes get
  values in your tests that did not respect min_value or max_value.
* When getting a Flaky error from an unreliable test it would have incorrectly
  displayed the example that caused it.
* 2.6 dependency on backports was incorrectly specified. This would only have
  caused you problems if you were building a universal wheel from Hypothesis,
  which is not how Hypothesis ships, so unless you're explicitly building wheels
  for your dependencies and support Python 2.6 plus a later version of Python
  this probably would never have affected you.
* If you use flatmap in a way that the strategy on the right hand side depends
  sensitively on the left hand side you may have occasionally seen Flaky errors
  caused by producing unreliable examples when minimizing a bug. This use case
  may still be somewhat fraught to be honest. This code is due a major rearchitecture
  for 1.8, but in the meantime this release fixes the only source of this error that
  I'm aware of.

---------------------------------------------------------------------
`1.7.1 <https://hypothesis.readthedocs.io/en/1.7.1/>`_ - 2015-06-29
---------------------------------------------------------------------

Codename: There is no 1.7.0.

A slight technical hitch with a premature upload means there's was a yanked
1.7.0 release. Oops.

The major feature of this release is Python 2.6 support. Thanks to Jeff Meadows
for doing most of the work there.

Other minor features

* strategies now has a permutations() function which returns a strategy
  yielding permutations of values from a given collection.
* if you have a flaky test it will print the exception that it last saw before
  failing with Flaky, even if you do not have verbose reporting on.
* Slightly experimental git merge script available as "python -m
  hypothesis.tools.mergedbs". Instructions on how to use it in the docstring
  of that file.

Bug fixes:

* Better performance from use of filter. In particular tests which involve large
  numbers of heavily filtered strategies should perform a lot better.
* floats() with a negative min_value would not have worked correctly (worryingly,
  it would have just silently failed to run any examples). This is now fixed.
* tests using sampled\_from would error if the number of sampled elements was smaller
  than min\_satisfying\_examples.


---------------------------------------------------------------------
`1.6.2 <https://hypothesis.readthedocs.io/en/1.6.2/>`_ - 2015-06-08
---------------------------------------------------------------------

This is just a few small bug fixes:

* Size bounds were not validated for values for a binary() strategy when
  reading examples from the database.
* sampled\_from is now in __all__ in hypothesis.strategies
* floats no longer consider negative integers to be simpler than positive
  non-integers
* Small floating point intervals now correctly count members, so if you have a
  floating point interval so narrow there are only a handful of values in it,
  this will no longer cause an error when Hypothesis runs out of values.

---------------------------------------------------------------------
`1.6.1 <https://hypothesis.readthedocs.io/en/1.6.1/>`_ - 2015-05-21
---------------------------------------------------------------------

This is a small patch release that fixes a bug where 1.6.0 broke the use
of flatmap with the deprecated API and assumed the passed in function returned
a SearchStrategy instance rather than converting it to a strategy.

---------------------------------------------------------------------
`1.6.0 <https://hypothesis.readthedocs.io/en/v1.6.0/>`_ - 2015-05-21
---------------------------------------------------------------------


This is a smallish release designed to fix a number of bugs and smooth out
some weird behaviours.

* Fix a critical bug in flatmap where it would reuse old strategies. If all
  your flatmap code was pure you're fine. If it's not, I'm surprised it's
  working at all. In particular if you want to use flatmap with django models,
  you desperately need to upgrade to this version.
* flatmap simplification performance should now be better in some cases where
  it previously had to redo work.
* Fix for a bug where invalid unicode data with surrogates could be generated
  during simplification (it was already filtered out during actual generation).
* The Hypothesis database is now keyed off the name of the test instead of the
  type of data. This makes much more sense now with the new strategies API and
  is generally more robust. This means you will lose old examples on upgrade.
* The database will now not delete values which fail to deserialize correctly,
  just skip them. This is to handle cases where multiple incompatible strategies
  share the same key.
* find now also saves and loads values from the database, keyed off a hash of the
  function you're finding from.
* Stateful tests now serialize and load values from the database. They should have
  before, really. This was a bug.
* Passing a different verbosity level into a test would not have worked entirely
  correctly, leaving off some messages. This is now fixed.
* Fix a bug where derandomized tests with unicode characters in the function
  body would error on Python 2.7.


---------------------------------------------------------------------
`1.5.0 <https://hypothesis.readthedocs.io/en/v1.5.0/>`_ - 2015-05-14
---------------------------------------------------------------------


Codename: Strategic withdrawal.

The purpose of this release is a radical simplification of the API for building
strategies. Instead of the old approach of @strategy.extend and things that
get converted to strategies, you just build strategies directly.

The old method of defining strategies will still work until Hypothesis 2.0,
because it's a major breaking change, but will now emit deprecation warnings.

The new API is also a lot more powerful as the functions for defining strategies
give you a lot of dials to turn. See :doc:`the updated data section <data>` for
details.

Other changes:

  * Mixing keyword and positional arguments in a call to @given is deprecated as well.
  * There is a new setting called 'strict'. When set to True, Hypothesis will raise
    warnings instead of merely printing them. Turning it on by default is inadvisable because
    it means that Hypothesis minor releases can break your code, but it may be useful for
    making sure you catch all uses of deprecated APIs.
  * max_examples in settings is now interpreted as meaning the maximum number
    of unique (ish) examples satisfying assumptions. A new setting max_iterations
    which defaults to a larger value has the old interpretation.
  * Example generation should be significantly faster due to a new faster parameter
    selection algorithm. This will mostly show up for simple data types - for complex
    ones the parameter selection is almost certainly dominated.
  * Simplification has some new heuristics that will tend to cut down on cases
    where it could previously take a very long time.
  * timeout would previously not have been respected in cases where there were a lot
    of duplicate examples. You probably wouldn't have previously noticed this because
    max_examples counted duplicates, so this was very hard to hit in a way that mattered.
  * A number of internal simplifications to the SearchStrategy API.
  * You can now access the current Hypothesis version as hypothesis.__version__.
  * A top level function is provided for running the stateful tests without the
    TestCase infrastructure.

---------------------------------------------------------------------
`1.4.0 <https://hypothesis.readthedocs.io/en/v1.4.0/>`_ - 2015-05-04
---------------------------------------------------------------------

Codename: What a state.

The *big* feature of this release is the new and slightly experimental
stateful testing API. You can read more about that in :doc:`the
appropriate section <stateful>`.

Two minor features the were driven out in the course of developing this:

* You can now set settings.max_shrinks to limit the number of times
  Hypothesis will try to shrink arguments to your test. If this is set to
  <= 0 then Hypothesis will not rerun your test and will just raise the
  failure directly. Note that due to technical limitations if max_shrinks
  is <= 0 then Hypothesis will print *every* example it calls your test
  with rather than just the failing one. Note also that I don't consider
  settings max_shrinks to zero a sensible way to run your tests and it
  should really be considered a debug feature.
* There is a new debug level of verbosity which is even *more* verbose than
  verbose. You probably don't want this.

Breakage of semi-public SearchStrategy API:

* It is now a required invariant of SearchStrategy that if u simplifies to
  v then it is not the case that strictly_simpler(u, v). i.e. simplifying
  should not *increase* the complexity even though it is not required to
  decrease it. Enforcing this invariant lead to finding some bugs where
  simplifying of integers, floats and sets was suboptimal.
* Integers in basic data are now required to fit into 64 bits. As a result
  python integer types are now serialized as strings, and some types have
  stopped using quite so needlessly large random seeds.

Hypothesis Stateful testing was then turned upon Hypothesis itself, which lead
to an amazing number of minor bugs being found in Hypothesis itself.

Bugs fixed (most but not all from the result of stateful testing) include:

* Serialization of streaming examples was flaky in a way that you would
  probably never notice: If you generate a template, simplify it, serialize
  it, deserialize it, serialize it again and then deserialize it you would
  get the original stream instead of the simplified one.
* If you reduced max_examples below the number of examples already saved in
  the database, you would have got a ValueError. Additionally, if you had
  more than max_examples in the database all of them would have been
  considered.
* @given will no longer count duplicate examples (which it never called
  your function with) towards max_examples. This may result in your tests
  running slower, but that's probably just because they're trying more
  examples.
* General improvements to example search which should result in better
  performance and higher quality examples. In particular parameters which
  have a history of producing useless results will be more aggressively
  culled. This is useful both because it decreases the chance of useless
  examples and also because it's much faster to not check parameters which
  we were unlikely to ever pick!
* integers_from and lists of types with only one value (e.g. [None]) would
  previously have had a very high duplication rate so you were probably
  only getting a handful of examples. They now have a much lower
  duplication rate, as well as the improvements to search making this
  less of a problem in the first place.
* You would sometimes see simplification taking significantly longer than
  your defined timeout. This would happen because timeout was only being
  checked after each *successful* simplification, so if Hypothesis was
  spending a lot of time unsuccessfully simplifying things it wouldn't
  stop in time. The timeout is now applied for unsuccessful simplifications
  too.
* In Python 2.7, integers_from strategies would have failed during
  simplification with an OverflowError if their starting point was at or
  near to the maximum size of a 64-bit integer.
* flatmap and map would have failed if called with a function without a
  __name__ attribute.
* If max_examples was less than min_satisfying_examples this would always
  error. Now min_satisfying_examples is capped to max_examples. Note that
  if you have assumptions to satisfy here this will still cause an error.

Some minor quality improvements:

* Lists of streams, flatmapped strategies and basic strategies should now
  now have slightly better simplification.

---------------------------------------------------------------------
`1.3.0 <https://hypothesis.readthedocs.io/en/v1.3.0/>`_ - 2015-05-22
---------------------------------------------------------------------

New features:

* New verbosity level API for printing intermediate results and exceptions.
* New specifier for strings generated from a specified alphabet.
* Better error messages for tests that are failing because of a lack of enough
  examples.

Bug fixes:

* Fix error where use of ForkingTestCase would sometimes result in too many
  open files.
* Fix error where saving a failing example that used flatmap could error.
* Implement simplification for sampled_from, which apparently never supported
  it previously. Oops.


General improvements:

* Better range of examples when using one_of or sampled_from.
* Fix some pathological performance issues when simplifying lists of complex
  values.
* Fix some pathological performance issues when simplifying examples that
  require unicode strings with high codepoints.
* Random will now simplify to more readable examples.


---------------------------------------------------------------------
`1.2.1 <https://hypothesis.readthedocs.io/en/v1.2.1/>`_ - 2015-04-16
---------------------------------------------------------------------

A small patch release for a bug in the new executors feature. Tests which require
doing something to their result in order to fail would have instead reported as
flaky.

---------------------------------------------------------------------
`1.2.0 <https://hypothesis.readthedocs.io/en/v1.2.0/>`_ - 2015-04-15
---------------------------------------------------------------------

Codename: Finders keepers.

A bunch of new features and improvements.

* Provide a mechanism for customizing how your tests are executed.
* Provide a test runner that forks before running each example. This allows
  better support for testing native code which might trigger a segfault or a C
  level assertion failure.
* Support for using Hypothesis to find examples directly rather than as just as
  a test runner.
* New streaming type which lets you generate infinite lazily loaded streams of
  data - perfect for if you need a number of examples but don't know how many.
* Better support for large integer ranges. You can now use integers_in_range
  with ranges of basically any size. Previously large ranges would have eaten
  up all your memory and taken forever.
* Integers produce a wider range of data than before - previously they would
  only rarely produce integers which didn't fit into a machine word. Now it's
  much more common. This percolates to other numeric types which build on
  integers.
* Better validation of arguments to @given. Some situations that would
  previously have caused silently wrong behaviour will now raise an error.
* Include +/- sys.float_info.max in the set of floating point edge cases that
  Hypothesis specifically tries.
* Fix some bugs in floating point ranges which happen when given
  +/- sys.float_info.max as one of the endpoints... (really any two floats that
  are sufficiently far apart so that x, y are finite but y - x is infinite).
  This would have resulted in generating infinite values instead of ones inside
  the range.

---------------------------------------------------------------------
`1.1.1 <https://hypothesis.readthedocs.io/en/v1.1.1/>`_ - 2015-04-07
---------------------------------------------------------------------

Codename: Nothing to see here

This is just a patch release put out because it fixed some internal bugs that would
block the Django integration release but did not actually affect anything anyone could
previously have been using. It also contained a minor quality fix for floats that
I'd happened to have finished in time.

* Fix some internal bugs with object lifecycle management that were impossible to
  hit with the previously released versions but broke hypothesis-django.
* Bias floating point numbers somewhat less aggressively towards very small numbers


---------------------------------------------------------------------
`1.1.0 <https://hypothesis.readthedocs.io/en/v1.1.0/>`_ - 2015-04-06
---------------------------------------------------------------------

Codename: No-one mention the M word.

* Unicode strings are more strongly biased towards ascii characters. Previously they
  would generate all over the space. This is mostly so that people who try to
  shape their unicode strings with assume() have less of a bad time.
* A number of fixes to data deserialization code that could theoretically have
  caused mysterious bugs when using an old version of a Hypothesis example
  database with a newer version. To the best of my knowledge a change that could
  have triggered this bug has never actually been seen in the wild. Certainly
  no-one ever reported a bug of this nature.
* Out of the box support for Decimal and Fraction.
* new dictionary specifier for dictionaries with variable keys.
* Significantly faster and higher quality simplification, especially for
  collections of data.
* New filter() and flatmap() methods on Strategy for better ways of building
  strategies out of other strategies.
* New BasicStrategy class which allows you to define your own strategies from
  scratch without needing an existing matching strategy or being exposed to the
  full horror or non-public nature of the SearchStrategy interface.


---------------------------------------------------------------------
`1.0.0 <https://hypothesis.readthedocs.io/en/v1.0.0/>`_ - 2015-03-27
---------------------------------------------------------------------

Codename: Blast-off!

There are no code changes in this release. This is precisely the 0.9.2 release
with some updated documentation.

------------------
0.9.2 - 2015-03-26
------------------

Codename: T-1 days.

* floats_in_range would not actually have produced floats_in_range unless that
  range happened to be (0, 1). Fix this.

------------------
0.9.1 - 2015-03-25
------------------

Codename: T-2 days.

* Fix a bug where if you defined a strategy using map on a lambda then the results would not be saved in the database.
* Significant performance improvements when simplifying examples using lists, strings or bounded integer ranges.

------------------
0.9.0 - 2015-03-23
------------------

Codename: The final countdown

This release could also be called 1.0-RC1.

It contains a teeny tiny bugfix, but the real point of this release is to declare
feature freeze. There will be zero functionality changes between 0.9.0 and 1.0 unless
something goes really really wrong. No new features will be added, no breaking API changes
will occur, etc. This is the final shakedown before I declare Hypothesis stable and ready
to use and throw a party to celebrate.

Bug bounty for any bugs found between now and 1.0: I will buy you a drink (alcoholic,
caffeinated, or otherwise) and shake your hand should we ever find ourselves in the
same city at the same time.

The one tiny bugfix:

* Under pypy, databases would fail to close correctly when garbage collected, leading to a memory leak and a confusing error message if you were repeatedly creating databases and not closing them. It is very unlikely you were doing this and the chances of you ever having noticed this bug are very low.

------------------
0.7.2 - 2015-03-22
------------------

Codename: Hygienic macros or bust

* You can now name an argument to @given 'f' and it won't break (issue #38)
* strategy_test_suite is now named strategy_test_suite as the documentation claims and not in fact strategy_test_suitee
* Settings objects can now be used as a context manager to temporarily override the default values inside their context.


------------------
0.7.1 - 2015-03-21
------------------

Codename: Point releases go faster

* Better string generation by parametrizing by a limited alphabet
* Faster string simplification - previously if simplifying a string with high range unicode characters it would try every unicode character smaller than that. This was pretty pointless. Now it stops after it's a short range (it can still reach smaller ones through recursive calls because of other simplifying operations).
* Faster list simplification by first trying a binary chop down the middle
* Simultaneous simplification of identical elements in a list. So if a bug only triggers when you have duplicates but you drew e.g. [-17, -17], this will now simplify to [0, 0].


-------------------
0.7.0, - 2015-03-20
-------------------

Codename: Starting to look suspiciously real

This is probably the last minor release prior to 1.0. It consists of stability
improvements, a few usability things designed to make Hypothesis easier to try
out, and filing off some final rough edges from the API.

* Significant speed and memory usage improvements
* Add an example() method to strategy objects to give an example of the sort of data that the strategy generates.
* Remove .descriptor attribute of strategies
* Rename descriptor_test_suite to strategy_test_suite
* Rename the few remaining uses of descriptor to specifier (descriptor already has a defined meaning in Python)


---------------------------------------------------------
0.6.0 - 2015-03-13
---------------------------------------------------------

Codename: I'm sorry, were you using that API?

This is primarily a "simplify all the weird bits of the API" release. As a result there are a lot of breaking changes. If
you just use @given with core types then you're probably fine.

In particular:

* Stateful testing has been removed from the API
* The way the database is used has been rendered less useful (sorry). The feature for reassembling values saved from other
  tests doesn't currently work. This will probably be brought back in post 1.0.
* SpecificationMapper is no longer a thing. Instead there is an ExtMethod called strategy which you extend to specify how
  to convert other types to strategies.
* Settings are now extensible so you can add your own for configuring a strategy
* MappedSearchStrategy no longer needs an unpack method
* Basically all the SearchStrategy internals have changed massively. If you implemented SearchStrategy directly rather than
  using MappedSearchStrategy talk to me about fixing it.
* Change to the way extra packages work. You now specify the package. This
  must have a load() method. Additionally any modules in the package will be
  loaded in under hypothesis.extra

Bug fixes:

* Fix for a bug where calling falsify on a lambda with a non-ascii character
  in its body would error.

Hypothesis Extra:

hypothesis-fakefactory\: An extension for using faker data in hypothesis. Depends
    on fake-factory.

------------------
0.5.0 - 2015-02-10
------------------

Codename: Read all about it.

Core hypothesis:

* Add support back in for pypy and python 3.2
* @given functions can now be invoked with some arguments explicitly provided. If all arguments that hypothesis would have provided are passed in then no falsification is run.
* Related to the above, this means that you can now use pytest fixtures and mark.parametrize with Hypothesis without either interfering with the other.
* Breaking change: @given no longer works for functions with varargs (varkwargs are fine). This might be added back in at a later date.
* Windows is now fully supported. A limited version (just the tests with none of the extras) of the test suite is run on windows with each commit so it is now a first class citizen of the Hypothesis world.
* Fix a bug for fuzzy equality of equal complex numbers with different reprs (this can happen when one coordinate is zero). This shouldn't affect users - that feature isn't used anywhere public facing.
* Fix generation of floats on windows and 32-bit builds of python. I was using some struct.pack logic that only worked on certain word sizes.
* When a test times out and hasn't produced enough examples this now raises a Timeout subclass of Unfalsifiable.
* Small search spaces are better supported. Previously something like a @given(bool, bool) would have failed because it couldn't find enough examples. Hypothesis is now aware of the fact that these are small search spaces and will not error in this case.
* Improvements to parameter search in the case of hard to satisfy assume. Hypothesis will now spend less time exploring parameters that are unlikely to provide anything useful.
* Increase chance of generating "nasty" floats
* Fix a bug that would have caused unicode warnings if you had a sampled_from that was mixing unicode and byte strings.
* Added a standard test suite that you can use to validate a custom strategy you've defined is working correctly.

Hypothesis extra:

First off, introducing Hypothesis extra packages!

These are packages that are separated out from core Hypothesis because they have one or more dependencies. Every
hypothesis-extra package is pinned to a specific point release of Hypothesis and will have some version requirements
on its dependency. They use entry_points so you will usually not need to explicitly import them, just have them installed
on the path.

This release introduces two of them:

hypothesis-datetime:

Does what it says on the tin: Generates datetimes for Hypothesis. Just install the package and datetime support will start
working.

Depends on pytz for timezone support

hypothesis-pytest:

A very rudimentary pytest plugin. All it does right now is hook the display of falsifying examples into pytest reporting.

Depends on pytest.


------------------
0.4.3 - 2015-02-05
------------------

Codename: TIL narrow Python builds are a thing

This just fixes the one bug.

* Apparently there is such a thing as a "narrow python build" and OS X ships with these by default
  for python 2.7. These are builds where you only have two bytes worth of unicode. As a result,
  generating unicode was completely broken on OS X. Fix this by only generating unicode codepoints
  in the range supported by the system.


------------------
0.4.2 - 2015-02-04
------------------

Codename: O(dear)

This is purely a bugfix release:

* Provide sensible external hashing for all core types. This will significantly improve
  performance of tracking seen examples which happens in literally every falsification
  run. For Hypothesis fixing this cut 40% off the runtime of the test suite. The behaviour
  is quadratic in the number of examples so if you're running the default configuration
  this will be less extreme (Hypothesis's test suite runs at a higher number of examples
  than default), but you should still see a significant improvement.
* Fix a bug in formatting of complex numbers where the string could get incorrectly truncated.


------------------
0.4.1 - 2015-02-03
------------------

Codename: Cruel and unusual edge cases

This release is mostly about better test case generation.

Enhancements:

* Has a cool release name
* text_type (str in python 3, unicode in python 2) example generation now
  actually produces interesting unicode instead of boring ascii strings.
* floating point numbers are generated over a much wider range, with particular
  attention paid to generating nasty numbers - nan, infinity, large and small
  values, etc.
* examples can be generated using pieces of examples previously saved in the
  database. This allows interesting behaviour that has previously been discovered
  to be propagated to other examples.
* improved parameter exploration algorithm which should allow it to more reliably
  hit interesting edge cases.
* Timeout can now be disabled entirely by setting it to any value <= 0.


Bug fixes:

* The descriptor on a OneOfStrategy could be wrong if you had descriptors which
  were equal but should not be coalesced. e.g. a strategy for one_of((frozenset({int}), {int}))
  would have reported its descriptor as {int}. This is unlikely to have caused you
  any problems
* If you had strategies that could produce NaN (which float previously couldn't but
  e.g. a Just(float('nan')) could) then this would have sent hypothesis into an infinite
  loop that would have only been terminated when it hit the timeout.
* Given elements that can take a long time to minimize, minimization of floats or tuples
  could be quadratic or worse in the that value. You should now see much better performance
  for simplification, albeit at some cost in quality.

Other:

* A lot of internals have been been rewritten. This shouldn't affect you at all, but
  it opens the way for certain of hypothesis's oddities to be a lot more extensible by
  users. Whether this is a good thing may be up for debate...


------------------
0.4.0 - 2015-01-21
------------------

FLAGSHIP FEATURE: Hypothesis now persists examples for later use. It stores
data in a local SQLite database and will reuse it for all tests of the same
type.

LICENSING CHANGE: Hypothesis is now released under the Mozilla Public License
2.0. This applies to all versions from 0.4.0 onwards until further notice.
The previous license remains applicable to all code prior to 0.4.0.

Enhancements:

* Printing of failing examples. I was finding that the pytest runner was not
  doing a good job of displaying these, and that Hypothesis itself could do
  much better.
* Drop dependency on six for cross-version compatibility. It was easy
  enough to write the shim for the small set of features that we care about
  and this lets us avoid a moderately complex dependency.
* Some improvements to statistical distribution of selecting from small (<=
  3 elements)
* Improvements to parameter selection for finding examples.

Bugs fixed:

* could_have_produced for lists, dicts and other collections would not have
  examined the elements and thus when using a union of different types of
  list this could result in Hypothesis getting confused and passing a value
  to the wrong strategy. This could potentially result in exceptions being
  thrown from within simplification.
* sampled_from would not work correctly on a single element list.
* Hypothesis could get *very* confused by values which are
  equal despite having different types being used in descriptors. Hypothesis
  now has its own more specific version of equality it uses for descriptors
  and tracking. It is always more fine grained than Python equality: Things
  considered != are not considered equal by hypothesis, but some things that
  are considered == are distinguished. If your test suite uses both frozenset
  and set tests this bug is probably affecting you.

------------------
0.3.2 - 2015-01-16
------------------

* Fix a bug where if you specified floats_in_range with integer arguments
  Hypothesis would error in example simplification.
* Improve the statistical distribution of the floats you get for the
  floats_in_range strategy. I'm not sure whether this will affect users in
  practice but it took my tests for various conditions from flaky to rock
  solid so it at the very least improves discovery of the artificial cases
  I'm looking for.
* Improved repr() for strategies and RandomWithSeed instances.
* Add detection for flaky test cases where hypothesis managed to find an
  example which breaks it but on the final invocation of the test it does
  not raise an error. This will typically happen with too much recursion
  errors but could conceivably happen in other circumstances too.
* Provide a "derandomized" mode. This allows you to run hypothesis with
  zero real randomization, making your build nice and deterministic. The
  tests run with a seed calculated from the function they're testing so you
  should still get a good distribution of test cases.
* Add a mechanism for more conveniently defining tests which just sample
  from some collection.
* Fix for a really subtle bug deep in the internals of the strategy table.
  In some circumstances if you were to define instance strategies for both
  a parent class and one or more of its subclasses you would under some
  circumstances get the strategy for the wrong superclass of an instance.
  It is very unlikely anyone has ever encountered this in the wild, but it
  is conceivably possible given that a mix of namedtuple and tuple are used
  fairly extensively inside hypothesis which do exhibit this pattern of
  strategy.


------------------
0.3.1 - 2015-01-13
------------------

* Support for generation of frozenset and Random values
* Correct handling of the case where a called function mutates it argument.
  This involved introducing a notion of a strategies knowing how to copy
  their argument. The default method should be entirely acceptable and the
  worst case is that it will continue to have the old behaviour if you
  don't mark your strategy as mutable, so this shouldn't break anything.
* Fix for a bug where some strategies did not correctly implement
  could_have_produced. It is very unlikely that any of these would have
  been seen in the wild, and the consequences if they had been would have
  been minor.
* Re-export the @given decorator from the main hypothesis namespace. It's
  still available at the old location too.
* Minor performance optimisation for simplifying long lists.


------------------
0.3.0 - 2015-01-12
------------------

* Complete redesign of the data generation system. Extreme breaking change
  for anyone who was previously writing their own SearchStrategy
  implementations. These will not work any more and you'll need to modify
  them.
* New settings system allowing more global and modular control of Verifier
  behaviour.
* Decouple SearchStrategy from the StrategyTable. This leads to much more
  composable code which is a lot easier to understand.
* A significant amount of internal API renaming and moving. This may also
  break your code.
* Expanded available descriptors, allowing for generating integers or
  floats in a specific range.
* Significantly more robust. A very large number of small bug fixes, none
  of which anyone is likely to have ever noticed.
* Deprecation of support for pypy and python 3 prior to 3.3. 3.3 and 3.4.
  Supported versions are 2.7.x, 3.3.x, 3.4.x. I expect all of these to
  remain officially supported for a very long time. I would not be
  surprised to add pypy support back in later but I'm not going to do so
  until I know someone cares about it. In the meantime it will probably
  still work.


------------------
0.2.2 - 2015-01-08
------------------

* Fix an embarrassing complete failure of the installer caused by my being
  bad at version control


------------------
0.2.1 - 2015-01-07
------------------

* Fix a bug in the new stateful testing feature where you could make
  __init__ a @requires method. Simplification would not always work if the
  prune method was able to successfully shrink the test.


------------------
0.2.0 - 2015-01-07
------------------

* It's aliiive.
* Improve python 3 support using six.
* Distinguish between byte and unicode types.
* Fix issues where FloatStrategy could raise.
* Allow stateful testing to request constructor args.
* Fix for issue where test annotations would timeout based on when the
  module was loaded instead of when the test started


------------------
0.1.4 - 2013-12-14
------------------

* Make verification runs time bounded with a configurable timeout


------------------
0.1.3 - 2013-05-03
------------------

* Bugfix: Stateful testing behaved incorrectly with subclassing.
* Complex number support
* support for recursive strategies
* different error for hypotheses with unsatisfiable assumptions

------------------
0.1.2 - 2013-03-24
------------------

* Bugfix: Stateful testing was not minimizing correctly and could
  throw exceptions.
* Better support for recursive strategies.
* Support for named tuples.
* Much faster integer generation.


------------------
0.1.1 - 2013-03-24
------------------

* Python 3.x support via 2to3.
* Use new style classes (oops).


------------------
0.1.0 - 2013-03-23
------------------

* Introduce stateful testing.
* Massive rewrite of internals to add flags and strategies.


------------------
0.0.5 - 2013-03-13
------------------

* No changes except trying to fix packaging

------------------
0.0.4 - 2013-03-13
------------------

* No changes except that I checked in a failing test case for 0.0.3
  so had to replace the release. Doh

------------------
0.0.3 - 2013-03-13
------------------

* Improved a few internals.
* Opened up creating generators from instances as a general API.
* Test integration.

------------------
0.0.2 - 2013-03-12
------------------

* Starting to tighten up on the internals.
* Change API to allow more flexibility in configuration.
* More testing.

------------------
0.0.1 - 2013-03-10
------------------

* Initial release.
* Basic working prototype. Demonstrates idea, probably shouldn't be used.
