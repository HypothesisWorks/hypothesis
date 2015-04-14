=========
Changelog
=========

This is a record of all past Hypothesis releases and what went into them,
in reverse chronological order. All previous releases should still be available
on pip.

All Hypothesis releases since 1.0 are `semantically versioned <http://semver.org/>`,
with everything in this documentation considered public API.

----------------
1.2 - 2015-04-15
----------------

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

------------------
1.1.1 - 2015-04-07
------------------

Codename: Nothing to see here

This is just a patch release put out because it fixed some internal bugs that would
block the Django integration release but did not actually affect anything anyone could
previously have been using. It also contained a minor quality fix for floats that
I'd happened to have finished in time.

* Fix some internal bugs with object lifecycle management that were impossible to
  hit with the previously released versions but broke hypothesis-django.
* Bias floating point numbers somewhat less aggressively towards very small numbers


------------------
1.1.0 - 2015-04-06
------------------

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


------------------
1.0.0 - 2015-03-27
------------------

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
* Simultaneous simplification of identical elements in a list. So if a bug only trickers when you have duplicates but you drew e.g. [-17, -17], this will now simplify to [0, 0].


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
* Rename the few remaing uses of descriptor to specifier (descriptor already has a defined meaning in Python)


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

* Apparently there is such a thing as a "narrow python build" and OSX ships with these by default
  for python 2.7. These are builds where you only have two bytes worth of unicode. As a result,
  generating unicode was completely broken on OSX. Fix this by only generating unicode codepoints
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

LICENSING CHANGE: Hypothesis is now released under the Mozila Public License
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
  In some circumstances if you were to define instance stratagies for both
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
  bene minor.
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

* Fix an embarassing complete failure of the installer caused by my being
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
