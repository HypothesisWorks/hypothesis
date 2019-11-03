=========
Changelog
=========

This is a record of all past Hypothesis releases and what went into them,
in reverse chronological order. All previous releases should still be available
on pip.

Hypothesis APIs come in three flavours:

* Public: Hypothesis releases since 1.0 are `semantically versioned <https://semver.org/>`_
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

.. _v4.42.10:

--------------------
4.42.10 - 2019-11-03
--------------------

This release fixes :func:`~hypothesis.strategies.from_type` when used with
bounded or constrained :obj:`python:typing.TypeVar` objects (:issue:`2094`).

Previously, distinct typevars with the same constraints would be treated as all
single typevar, and in cases where a typevar bound was resolved to a union of
subclasses this could result in mixed types being generated for that typevar.

.. _v4.42.9:

-------------------
4.42.9 - 2019-11-03
-------------------

This patch ensures that the default value :func:`~hypothesis.extra.numpy.broadcastable_shapes`
chooses for ``max_dims`` is always valid (at most 32), even if you pass ``min_dims=32``.

.. _v4.42.8:

-------------------
4.42.8 - 2019-11-02
-------------------

This patch ensures that we only add profile information to the pytest header
if running either pytest or Hypothesis in verbose mode, matching the
`builtin cache plugin <https://docs.pytest.org/en/latest/cache.html>`__
(:issue:`2155`).

.. _v4.42.7:

-------------------
4.42.7 - 2019-11-02
-------------------

This patch makes stateful step printing expand the result of a step into
multiple variables when a MultipleResult is returned (:issue:`2139`).
Thanks to Joseph Weston for reporting and fixing this bug!

.. _v4.42.6:

-------------------
4.42.6 - 2019-11-02
-------------------

This release fixes a bug (:issue:`2166`) where a Unicode character info
cache file was generated but never used on subsequent test runs, causing tests
to run more slowly than they should have.

Thanks to Robert Knight for this bugfix!

.. _v4.42.5:

-------------------
4.42.5 - 2019-11-01
-------------------

This patch corrects some internal documentation.  There is no user-visible change.

.. _v4.42.4:

-------------------
4.42.4 - 2019-11-01
-------------------

This release fixes a bug (:issue:`2160`) where decorators applied after
:func:`@settings <hypothesis.settings>` and before
:func:`@given <hypothesis.given>` were ignored.

Thanks to Tom Milligan for this bugfix!

.. _v4.42.3:

-------------------
4.42.3 - 2019-10-30
-------------------

This release updates Hypothesis's formatting to the new version of black, and
has absolutely no user visible effect.

.. _v4.42.2:

-------------------
4.42.2 - 2019-10-30
-------------------

This release fixes a bug in :func:`~hypothesis.strategies.recursive` which would
have meant that in practice ``max_leaves`` was treated as if it was lower than
it actually is - specifically it would be capped at the largest power of two
smaller than it. It is now handled correctly.

.. _v4.42.1:

-------------------
4.42.1 - 2019-10-30
-------------------

Python 3.8's new :class:`python:typing.SupportsIndex` type - see :pep:`357`
for details - is now  supported in :func:`~hypothesis.strategies.from_type`.

Thanks to Grigorios Giannakopoulos for the patch!

.. _v4.42.0:

-------------------
4.42.0 - 2019-10-27
-------------------

This release significantly simplifies Hypothesis's internal logic for data
generation, by removing a number of heuristics of questionable or unproven
value.

The results of this change will vary significantly from test to test. Most
test suites will see significantly faster data generation and lower memory
usage. The "quality" of the generated data may go up or down depending on your
particular test suites.

If you see any significant regressions in Hypothesis's ability to find bugs in
your code as a result of this release, please file an issue to let us know.

Users of the new  :ref:`targeted property-based testing <targeted-search>`
functionality are reasonably likely to see *improvements* in data generation,
as this release changes the search algorithm for targeted property based
testing to one that is more likely to be productive than the existing approach.

.. _v4.41.3:

-------------------
4.41.3 - 2019-10-21
-------------------

This patch is to ensure that our internals remain comprehensible to
:pypi:`mypy` 0.740 - there is no user-visible change.

.. _v4.41.2:

-------------------
4.41.2 - 2019-10-17
-------------------

This patch changes some internal hashes to SHA384, to better support
users subject to FIPS-140. There is no user-visible API change.

Thanks to Paul Kehrer for this contribution!

.. _v4.41.1:

-------------------
4.41.1 - 2019-10-16
-------------------

This release makes ``--hypothesis-show-statistics`` much more useful for
tests using a :class:`~hypothesis.stateful.RuleBasedStateMachine`, by
simplifying the reprs so that events are aggregated correctly.

.. _v4.41.0:

-------------------
4.41.0 - 2019-10-16
-------------------

This release upgrades the :func:`~hypothesis.strategies.fixed_dictionaries`
strategy to support ``optional`` keys (:issue:`1913`).

.. _v4.40.2:

-------------------
4.40.2 - 2019-10-16
-------------------

This release makes some minor internal changes in support of improving the
Hypothesis test suite. It should not have any user visible impact.

.. _v4.40.1:

-------------------
4.40.1 - 2019-10-14
-------------------

This release changes how Hypothesis checks if a parameter to a test function is a mock object.
It is unlikely to have any noticeable effect, but may result in a small performance improvement,
especially for test functions where a mock object is being passed as the first argument.

.. _v4.40.0:

-------------------
4.40.0 - 2019-10-09
-------------------

This release fixes a bug where our example database logic did not distinguish
between failing examples based on arguments from a ``@pytest.mark.parametrize(...)``.
This could in theory cause data loss if a common failure overwrote a rare one, and
in practice caused occasional file-access collisions in highly concurrent workloads
(e.g. during a 300-way parametrize on 16 cores).

For internal reasons this also involves bumping the minimum supported version of
:pypi:`pytest` to 4.3

Thanks to Peter C Kroon for the Hacktoberfest patch!

.. _v4.39.3:

-------------------
4.39.3 - 2019-10-09
-------------------

This patch improves our type hints on the :func:`~hypothesis.strategies.emails`,
:func:`~hypothesis.strategies.functions`, :func:`~hypothesis.strategies.integers`,
:func:`~hypothesis.strategies.iterables`, and :func:`~hypothesis.strategies.slices`
strategies, as well as the ``.filter()`` method.

There is no runtime change, but if you use :pypi:`mypy` or a similar
type-checker on your tests the results will be a bit more precise.

.. _v4.39.2:

-------------------
4.39.2 - 2019-10-09
-------------------

This patch improves the performance of unique collections such as
:func:`~hypothesis.strategies.sets` of :func:`~hypothesis.strategies.just`
or :func:`~hypothesis.strategies.booleans` strategies.  They were already
pretty good though, so you're unlikely to notice much!

.. _v4.39.1:

-------------------
4.39.1 - 2019-10-09
-------------------

If a value in a dict passed to :func:`~hypothesis.strategies.fixed_dictionaries`
is not a strategy, Hypothesis now tells you which one.

.. _v4.39.0:

-------------------
4.39.0 - 2019-10-07
-------------------

This release adds the :func:`~hypothesis.extra.numpy.basic_indices` strategy,
to generate `basic indexes <https://docs.scipy.org/doc/numpy/reference/arrays.indexing.html>`__
for arrays of the specified shape (:issue:`1930`).

It generates tuples containing some mix of integers, :obj:`python:slice` objects,
``...`` (Ellipsis), and :obj:`numpy:numpy.newaxis`; which when used to index an array
of the specified shape produce either a scalar or a shared-memory view of the array.
Note that the index tuple may be longer or shorter than the array shape, and may
produce a view with another dimensionality again!

Thanks to Lampros Mountrakis, Ryan Soklaski, and Zac Hatfield-Dodds for their
collaboration on this surprisingly subtle strategy!

.. _v4.38.3:

-------------------
4.38.3 - 2019-10-04
-------------------

This patch defers creation of the ``.hypothesis`` directory until we have
something to store in it, meaning that it will appear when Hypothesis is
used rather than simply installed.

Thanks to Peter C Kroon for the Hacktoberfest patch!

.. _v4.38.2:

-------------------
4.38.2 - 2019-10-02
-------------------

This patch bumps our dependency on :pypi:`attrs` to ``>=19.2.0``;
but there are no user-visible changes to Hypothesis.

.. _v4.38.1:

-------------------
4.38.1 - 2019-10-01
-------------------

This is a comment-only patch which tells :pypi:`mypy` 0.730 to ignore
some internal compatibility shims we use to support older Pythons.

.. _v4.38.0:

-------------------
4.38.0 - 2019-10-01
-------------------

This release adds the :func:`hypothesis.target` function, which implements
**experimental** support for :ref:`targeted property-based testing <targeted-search>`
(:issue:`1779`).

By calling :func:`~hypothesis.target` in your test function, Hypothesis can
do a hill-climbing search for bugs.  If you can calculate a suitable metric
such as the load factor or length of a queue, this can help you find bugs with
inputs that are highly improbably from unguided generation - however good our
heuristics, example diversity, and deduplication logic might be.  After all,
those features are at work in targeted PBT too!

.. _v4.37.0:

-------------------
4.37.0 - 2019-09-28
-------------------

This release emits a warning if you use the ``.example()`` method of
a strategy in a non-interactive context.

:func:`~hypothesis.given` is a much better choice for writing tests,
whether you care about performance, minimal examples, reproducing
failures, or even just the variety of inputs that will be tested!

.. _v4.36.2:

-------------------
4.36.2 - 2019-09-20
-------------------

This patch disables part of the :mod:`typing`-based inference for the
:pypi:`attrs` package under Python 3.5.0, which has some incompatible
internal details (:issue:`2095`).

.. _v4.36.1:

-------------------
4.36.1 - 2019-09-17
-------------------

This patch fixes a bug in strategy inference for :pypi:`attrs` classes where
Hypothesis would fail to infer a strategy for attributes of a generic type
such as ``Union[int, str]`` or ``List[bool]`` (:issue:`2091`).

Thanks to Jonathan Gayvallet for the bug report and this patch!

.. _v4.36.0:

-------------------
4.36.0 - 2019-09-09
-------------------

This patch deprecates ``min_len`` or ``max_len`` of 0 in
:func:`~hypothesis.extra.numpy.byte_string_dtypes` and
:func:`~hypothesis.extra.numpy.unicode_string_dtypes`.
The lower limit is now 1.

Numpy uses a length of 0 in these dtypes to indicate an undetermined size,
chosen from the data at array creation.
However, as the :func:`~hypothesis.extra.numpy.arrays` strategy creates arrays
before filling them, strings were truncated to 1 byte.

.. _v4.35.1:

-------------------
4.35.1 - 2019-09-09
-------------------

This patch improves the messaging that comes from invalid size arguments
to collection strategies such as :func:`~hypothesis.strategies.lists`.

.. _v4.35.0:

-------------------
4.35.0 - 2019-09-04
-------------------

This release improves the :func:`~hypothesis.extra.lark.from_lark` strategy,
tightening argument validation and adding the ``explicit`` argument to allow use
with terminals that use ``@declare`` instead of a string or regular expression.

This feature is required to handle features such as indent and dedent tokens
in Python code, which can be generated with the :pypi:`hypothesmith` package.

.. _v4.34.0:

-------------------
4.34.0 - 2019-08-23
-------------------

The :func:`~hypothesis.strategies.from_type` strategy now knows to look up
the subclasses of abstract types, which cannot be instantiated directly.

This is very useful for :pypi:`hypothesmith` to support :pypi:`libCST`.

.. _v4.33.1:

-------------------
4.33.1 - 2019-08-21
-------------------

This patch works around a crash when an incompatible version of Numpy
is installed under PyPy 5.10 (Python 2.7).

If you are still using Python 2, please upgrade to Python 3 as soon
as possible - it will be unsupported at the end of this year.

.. _v4.33.0:

-------------------
4.33.0 - 2019-08-20
-------------------

This release improves the :func:`~hypothesis.provisional.domains`
strategy, as well as the :func:`~hypothesis.provisional.urls` and
the :func:`~hypothesis.strategies.emails` strategies which use it.
These strategies now use the full IANA list of Top Level Domains
and are correct as per :rfc:`1035`.

Passing tests using these strategies may now fail.

Thanks to `TechDragon <https://github.com/techdragon>`__ for this improvement.

.. _v4.32.3:

-------------------
4.32.3 - 2019-08-05
-------------------

This patch tidies up the repr of several ``settings``-related objects,
at runtime and in the documentation, and deprecates the undocumented
edge case that ``phases=None`` was treated like ``phases=tuple(Phase)``.

It *also* fixes :func:`~hypothesis.extra.lark.from_lark` with
:pypi:`lark 0.7.2 <lark-parser>` and later.

.. _v4.32.2:

-------------------
4.32.2 - 2019-07-30
-------------------

This patch updates some internal comments for :pypi:`mypy` 0.720.
There is no user-visible impact.

.. _v4.32.1:

-------------------
4.32.1 - 2019-07-29
-------------------

This release changes how the shrinker represents its progress internally. For large generated test cases
this should result in significantly less memory usage and possibly faster shrinking. Small generated
test cases may be slightly slower to shrink but this shouldn't be very noticeable.

.. _v4.32.0:

-------------------
4.32.0 - 2019-07-28
-------------------

This release makes :func:`~hypothesis.extra.numpy.arrays` more pedantic about
``elements`` strategies that cannot be exactly represented as array elements.

In practice, you will see new warnings if you were using a ``float16`` or
``float32`` dtype without passing :func:`~hypothesis.strategies.floats` the
``width=16`` or ``width=32`` arguments respectively.

The previous behaviour could lead to silent truncation, and thus some elements
being equal to an explicitly excluded bound (:issue:`1899`).

.. _v4.31.1:

-------------------
4.31.1 - 2019-07-28
-------------------

This patch changes an internal use of MD5 to SHA hashes, to better support
users subject to FIPS-140.  There is no user-visible or API change.

Thanks to Alex Gaynor for this patch.

.. _v4.31.0:

-------------------
4.31.0 - 2019-07-24
-------------------

This release simplifies the logic of the :attr:`~hypothesis.settings.print_blob` setting by removing the option to set it to ``PrintSettings.INFER``.
As a result the ``print_blob`` setting now takes a single boolean value, and the use of ``PrintSettings`` is deprecated.

.. _v4.28.2:

-------------------
4.28.2 - 2019-07-14
-------------------

This patch improves the docstrings of several Hypothesis strategies, by
clarifying markup and adding cross-references.  There is no runtime change.

Thanks to Elizabeth Williams and Serah Njambi Rono for their contributions
at the SciPy 2019 sprints!

.. _v4.28.1:

-------------------
4.28.1 - 2019-07-12
-------------------

This patch improves the behaviour of the :func:`~hypothesis.strategies.text`
strategy when passed an ``alphabet`` which is not a strategy.  The value is
now interpreted as ``whitelist_characters`` to :func:`~hypothesis.strategies.characters`
instead of a sequence for :func:`~hypothesis.strategies.sampled_from`, which
standardises the distribution of examples and the shrinking behaviour.

You can get the previous behaviour by using
``lists(sampled_from(alphabet)).map("".map)`` instead.

.. _v4.28.0:

-------------------
4.28.0 - 2019-07-11
-------------------

This release deprecates ``find()``.  The ``.example()`` method is a better
replacement if you want *an* example, and for the rare occasions where you
want the *minimal* example you can get it from :func:`@given <hypothesis.given>`.

:func:`@given <hypothesis.given>` has steadily outstripped ``find()`` in both
features and performance over recent years, and as we do not have the resources
to maintain and test both we think it is better to focus on just one.

.. _v4.27.0:

-------------------
4.27.0 - 2019-07-08
-------------------

This release refactors the implementation of the ``.example()`` method,
to more accurately represent the data which will be generated by
:func:`@given <hypothesis.given>`.

As a result, calling ``s.example()`` on an empty strategy ``s``
(such as :func:`~hypothesis.strategies.nothing`) now raises ``Unsatisfiable``
instead of the old ``NoExamples`` exception.

.. _v4.26.4:

-------------------
4.26.4 - 2019-07-07
-------------------

This patch ensures that the Pandas extra will keep working when Python 3.8
removes abstract base classes from the top-level :obj:`python:collections`
namespace.  This also fixes the relevant warning in Python 3.7, but there
is no other difference in behaviour and you do not need to do anything.

.. _v4.26.3:

-------------------
4.26.3 - 2019-07-05
-------------------

This release fixes  :issue:`2027`, by changing the way Hypothesis tries to generate distinct examples to be more efficient.

This may result in slightly different data distribution, and should improve generation performance in general,
but should otherwise have minimal user impact.

.. _v4.26.2:

-------------------
4.26.2 - 2019-07-04
-------------------

This release fixes :issue:`1864`, where some simple tests would perform very slowly,
because they would run many times with each subsequent run being progressively slower.
They will now stop after a more reasonable number of runs without hitting this problem.

Unless you are hitting exactly this issue, it is unlikely that this release will have any effect,
but certain classes of custom generators that are currently very slow may become a bit faster,
or start to trigger health check failures.

.. _v4.26.1:

-------------------
4.26.1 - 2019-07-04
-------------------

This release adds the strategy :func:`~hypothesis.extra.numpy.integer_array_indices`,
which generates tuples of Numpy arrays that can be used for
`advanced indexing <http://www.pythonlikeyoumeanit.com/Module3_IntroducingNumpy/AdvancedIndexing.html#Integer-Array-Indexing>`_
to select an array of a specified shape.

.. _v4.26.0:

-------------------
4.26.0 - 2019-07-04
-------------------

This release significantly improves the performance of drawing unique collections whose
elements are drawn from  :func:`~hypothesis.strategies.sampled_from`  strategies.

As a side effect, this detects an error condition that would previously have
passed silently: When the ``min_size`` argument on a collection with distinct elements
is greater than the number of elements being sampled, this will now raise an error.

.. _v4.25.1:

-------------------
4.25.1 - 2019-07-03
-------------------

This release removes some defunct internal functionality that was only being used
for testing. It should have no user visible impact.

.. _v4.25.0:

-------------------
4.25.0 - 2019-07-03
-------------------

This release deprecates and disables the ``buffer_size`` setting,
which should have been treated as a private implementation detail
all along.  We recommend simply deleting this settings argument.

.. _v4.24.6:

-------------------
4.24.6 - 2019-06-26
-------------------

This patch makes :func:`~hypothesis.strategies.datetimes` more efficient,
as it now handles short months correctly by construction instead of filtering.

.. _v4.24.5:

-------------------
4.24.5 - 2019-06-23
-------------------

This patch improves the development experience by simplifying the tracebacks
you will see when e.g. you have used the ``.map(...)`` method of a strategy
and the mapped function raises an exception.

No new exceptions can be raised, nor existing exceptions change anything but
their traceback.  We're simply using if-statements rather than exceptions for
control flow in a certain part of the internals!

.. _v4.24.4:

-------------------
4.24.4 - 2019-06-21
-------------------

This patch fixes :issue:`2014`, where our compatibility layer broke with version
3.7.4 of the :pypi:`typing` module backport on PyPI.

This issue only affects Python 2.  We remind users that Hypothesis, like many other
packages, `will drop Python 2 support on 2020-01-01 <https://python3statement.org>`__
and already has several features that are only available on Python 3.

.. _v4.24.3:

-------------------
4.24.3 - 2019-06-07
-------------------

This patch improves the implementation of an internal wrapper on Python 3.8
beta1 (and will break on the alphas; but they're not meant to be stable).
On other versions, there is no change at all.

Thanks to Daniel Hahler for the patch, and Victor Stinner for his work
on :bpo:`37032` that made it possible.

.. _v4.24.2:

-------------------
4.24.2 - 2019-06-06
-------------------

Deprecation messages for functions in ``hypothesis.extra.django.models`` now
explicitly name the deprecated function to make it easier to track down usages.
Thanks to Kristian Glass for this contribution!

.. _v4.24.1:

-------------------
4.24.1 - 2019-06-04
-------------------

This patch fixes :issue:`1999`, a spurious bug raised when a :func:`@st.composite <hypothesis.strategies.composite>` function was passed a keyword-only argument.

Thanks to Jim Nicholls for his fantastic bug report.

.. _v4.24.0:

-------------------
4.24.0 - 2019-05-29
-------------------

This release deprecates ``GenericStateMachine``, in favor of
:class:`~hypothesis.stateful.RuleBasedStateMachine`.  Rule-based stateful
testing is significantly faster, especially during shrinking.

If your use-case truly does not fit rule-based stateful testing,
we recommend writing a custom test function which drives your specific
control-flow using :func:`~hypothesis.strategies.data`.

.. _v4.23.9:

-------------------
4.23.9 - 2019-05-28
-------------------

This patch fixes a very rare example database issue with file permissions.

When running a test that uses both :func:`@given <hypothesis.given>`
and ``pytest.mark.parametrize``, using :pypi:`pytest-xdist` on Windows,
with failing examples in the database, two attempts to read a file could
overlap and we caught ``FileNotFound`` but not other ``OSError``\ s.

.. _v4.23.8:

-------------------
4.23.8 - 2019-05-26
-------------------

This patch has a minor cleanup of the internal engine.
There is no user-visible impact.

.. _v4.23.7:

-------------------
4.23.7 - 2019-05-26
-------------------

This patch clarifies some error messages when the test function signature
is incompatible with the arguments to :func:`@given <hypothesis.given>`,
especially when the :obj:`@settings() <hypothesis.settings>` decorator
is also used (:issue:`1978`).

.. _v4.23.6:

-------------------
4.23.6 - 2019-05-19
-------------------

This release adds the :pypi:`pyupgrade` fixer to our code style,
for consistent use of dict and set literals and comprehensions.

.. _v4.23.5:

-------------------
4.23.5 - 2019-05-16
-------------------

This release slightly simplifies a small part of the core engine.
There is no user-visible change.

.. _v4.23.4:

-------------------
4.23.4 - 2019-05-09
-------------------

Fixes a minor formatting issue the docstring of :func:`~hypothesis.strategies.from_type`

.. _v4.23.3:

-------------------
4.23.3 - 2019-05-09
-------------------

Adds a recipe to the docstring of :func:`~hypothesis.strategies.from_type`
that describes a means for drawing values for "everything except" a specified type.
This recipe is especially useful for writing tests that perform input-type validation.

.. _v4.23.2:

-------------------
4.23.2 - 2019-05-08
-------------------

This patch uses :pypi:`autoflake` to remove some pointless ``pass`` statements,
which improves our workflow but has no user-visible impact.

.. _v4.23.1:

-------------------
4.23.1 - 2019-05-08
-------------------

This patch fixes an OverflowError in
:func:`from_type(xrange) <hypothesis.strategies.from_type>` on Python 2.

It turns out that not only do the ``start`` and ``stop`` values have to
fit in a C long, but so does ``stop - start``.  We now handle this even
on 32bit platforms, but remind users that Python2 will not be supported
after 2019 without specific funding.

.. _v4.23.0:

-------------------
4.23.0 - 2019-05-08
-------------------

This release implements the :func:`~hypothesis.strategies.slices` strategy,
to generate slices of a length-``size`` sequence.

Thanks to Daniel J. West for writing this patch at the PyCon 2019 sprints!

.. _v4.22.3:

-------------------
4.22.3 - 2019-05-07
-------------------

This patch exposes :class:`~hypothesis.strategies.DataObject`, *solely*
to support more precise type hints.  Objects of this type are provided
by :func:`~hypothesis.strategies.data`, and can be used to draw examples
from strategies intermixed with your test code.

.. _v4.22.2:

-------------------
4.22.2 - 2019-05-07
-------------------

This patch fixes the very rare :issue:`1798` in
:func:`~hypothesis.extra.numpy.array_dtypes`,
which caused an internal error in our tests.

.. _v4.22.1:

-------------------
4.22.1 - 2019-05-07
-------------------

This patch fixes a rare bug in :func:`from_type(range) <hypothesis.strategies.from_type>`.

Thanks to Zebulun Arendsee for fixing the bug at the PyCon 2019 Sprints.

.. _v4.22.0:

-------------------
4.22.0 - 2019-05-07
-------------------

The ``unique_by`` argument to :obj:`~hypothesis.strategies.lists` now accepts a
tuple of callables such that every element of the generated list will be unique
with respect to each callable in the tuple (:issue:`1916`).

Thanks to Marco Sirabella for this feature at the PyCon 2019 sprints!

.. _v4.21.1:

-------------------
4.21.1 - 2019-05-06
-------------------

This patch cleans up the internals of :func:`~hypothesis.strategies.one_of`.
You may see a slight change to the distribution of examples from this strategy
but there is no change to the public API.

Thanks to Marco Sirabella for writing this patch at the PyCon 2019 sprints!

.. _v4.21.0:

-------------------
4.21.0 - 2019-05-05
-------------------

The :func:`~hypothesis.strategies.from_type` strategy now supports
:class:`python:slice` objects.

Thanks to Charlie El. Awbery for writing this feature at the
`PyCon 2019 Mentored Sprints <https://us.pycon.org/2019/hatchery/mentoredsprints/>`__.

.. _v4.20.0:

-------------------
4.20.0 - 2019-05-05
-------------------

This release improves the :func:`~hypothesis.extra.numpy.array_shapes`
strategy, to choose an appropriate default for ``max_side`` based on the
``min_side``, and ``max_dims`` based on the ``min_dims``.  An explicit
error is raised for dimensions greater than 32, which are not supported
by Numpy, as for other invalid combinations of arguments.

Thanks to Jenny Rouleau for writing this feature at the
`PyCon 2019 Mentored Sprints <https://us.pycon.org/2019/hatchery/mentoredsprints/>`__.

.. _v4.19.0:

-------------------
4.19.0 - 2019-05-05
-------------------

The :func:`~hypothesis.strategies.from_type` strategy now supports
:class:`python:range` objects (or ``xrange`` on Python 2).

Thanks to Katrina Durance for writing this feature at the
`PyCon 2019 Mentored Sprints <https://us.pycon.org/2019/hatchery/mentoredsprints/>`__.

.. _v4.18.3:

-------------------
4.18.3 - 2019-04-30
-------------------

This release fixes a very rare edge case in the test-case mutator,
which could cause an internal error with certain unusual tests.

.. _v4.18.2:

-------------------
4.18.2 - 2019-04-30
-------------------

This patch makes Hypothesis compatible with the Python 3.8 alpha, which
changed the representation of code objects to support positional-only
arguments.  Note however that Hypothesis does not (yet) support such
functions as e.g. arguments to :func:`~hypothesis.strategies.builds`
or inputs to :func:`@given <hypothesis.given>`.

Thanks to Paul Ganssle for identifying and fixing this bug.

.. _v4.18.1:

-------------------
4.18.1 - 2019-04-29
-------------------

This patch improves the performance of unique collections such as
:func:`~hypothesis.strategies.sets` when the elements are drawn from a
:func:`~hypothesis.strategies.sampled_from` strategy (:issue:`1115`).

.. _v4.18.0:

-------------------
4.18.0 - 2019-04-24
-------------------

This release adds the :func:`~hypothesis.strategies.functions` strategy,
which can be used to imitate your 'real' function for callbacks.

.. _v4.17.2:

-------------------
4.17.2 - 2019-04-19
-------------------

This release refactors stateful rule selection to share the new machinery
with :func:`~hypothesis.strategies.sampled_from` instead of using the original
independent implementation.

.. _v4.17.1:

-------------------
4.17.1 - 2019-04-16
-------------------

This patch allows Hypothesis to try a few more examples after finding the
first bug, in hopes of reporting multiple distinct bugs.  The heuristics
described in :issue:`847` ensure that we avoid wasting time on fruitless
searches, while still surfacing each bug as soon as possible.

.. _v4.17.0:

-------------------
4.17.0 - 2019-04-16
-------------------

This release adds the strategy :func:`~hypothesis.extra.numpy.broadcastable_shapes`,
which generates array shapes that are `broadcast-compatible <https://www.pythonlikeyoumeanit.com/Module3_IntroducingNumpy/Broadcasting.html#Rules-of-Broadcasting>`_
with a provided shape.

.. _v4.16.0:

-------------------
4.16.0 - 2019-04-12
-------------------

This release allows :func:`~hypothesis.strategies.register_type_strategy` to be used
with :obj:`python:typing.NewType` instances.  This may be useful to e.g. provide
only positive integers for :func:`from_type(UserId) <hypothesis.strategies.from_type>`
with a ``UserId = NewType('UserId', int)`` type.

Thanks to PJCampi for suggesting and writing the patch!

.. _v4.15.0:

-------------------
4.15.0 - 2019-04-09
-------------------

This release supports passing a :class:`~python:datetime.timedelta` as the
:obj:`~hypothesis.settings.deadline` setting, so you no longer have to remember
that the number is in milliseconds (:issue:`1900`).

Thanks to Damon Francisco for this change!

.. _v4.14.7:

-------------------
4.14.7 - 2019-04-09
-------------------

This patch makes the type annotations on ``hypothesis.extra.dateutil``
compatible with :pypi:`mypy` 0.700.

.. _v4.14.6:

-------------------
4.14.6 - 2019-04-07
-------------------

This release fixes a bug introduced in :ref:`Hypothesis 4.14.3 <v4.14.3>`
that would sometimes cause
:func:`sampled_from(...).filter(...) <hypothesis.strategies.sampled_from>`
to encounter an internal assertion failure when there are three or fewer
elements, and every element is rejected by the filter.

.. _v4.14.5:

-------------------
4.14.5 - 2019-04-05
-------------------

This patch takes the previous efficiency improvements to
:func:`sampled_from(...).filter(...) <hypothesis.strategies.sampled_from>`
strategies that reject most elements, and generalises them to also apply to
``sampled_from(...).filter(...).filter(...)`` and longer chains of filters.

.. _v4.14.4:

-------------------
4.14.4 - 2019-04-05
-------------------

This release fixes a bug that prevented
:func:`~hypothesis.strategies.random_module`
from correctly restoring the previous state of the ``random`` module.

The random state was instead being restored to a temporary deterministic
state, which accidentally caused subsequent tests to see the same random values
across multiple test runs.

.. _v4.14.3:

-------------------
4.14.3 - 2019-04-03
-------------------

This patch adds an internal special case to make
:func:`sampled_from(...).filter(...) <hypothesis.strategies.sampled_from>`
much more efficient when the filter rejects most elements (:issue:`1885`).

.. _v4.14.2:

-------------------
4.14.2 - 2019-03-31
-------------------

This patch improves the error message if the function ``f`` in
:ref:`s.flatmap(f) <flatmap>` does not return a strategy.

Thanks to Kai Chen for this change!

.. _v4.14.1:

-------------------
4.14.1 - 2019-03-30
-------------------

This release modifies how Hypothesis selects operations to run during shrinking,
by causing it to deprioritise previously useless classes of shrink until others have reached a fixed point.

This avoids certain pathological cases where the shrinker gets very close to finishing and then takes a very long time to finish the last small changes because it tries many useless shrinks for each useful one towards the end.
It also should cause a more modest improvement (probably no more than about 30%) in shrinking performance for most tests.

.. _v4.14.0:

-------------------
4.14.0 - 2019-03-19
-------------------

This release blocks installation of Hypothesis on Python 3.4, which
:PEP:`reached its end of life date on 2019-03-18 <429>`.

This should not be of interest to anyone but downstream maintainers -
if you are affected, migrate to a secure version of Python as soon as
possible or at least seek commercial support.

.. _v4.13.0:

-------------------
4.13.0 - 2019-03-19
-------------------

This release makes it an explicit error to call
:func:`floats(min_value=inf, exclude_min=True) <hypothesis.strategies.floats>` or
:func:`floats(max_value=-inf, exclude_max=True) <hypothesis.strategies.floats>`,
as there are no possible values that can be generated (:issue:`1859`).

:func:`floats(min_value=0.0, max_value=-0.0) <hypothesis.strategies.floats>`
is now deprecated.  While `0. == -0.` and we could thus generate either if
comparing by value, violating the sequence ordering of floats is a special
case we don't want or need.

.. _v4.12.1:

-------------------
4.12.1 - 2019-03-18
-------------------

This release should significantly reduce the amount of memory that Hypothesis uses for representing large test cases,
by storing information in a more compact representation and only unpacking it lazily when it is first needed.

.. _v4.12.0:

-------------------
4.12.0 - 2019-03-18
-------------------

This update adds the :obj:`~hypothesis.settings.report_multiple_bugs` setting,
which you can use to disable multi-bug reporting and only raise whichever bug
had the smallest minimal example.  This is occasionally useful when using a
debugger or tools that annotate tracebacks via introspection.

.. _v4.11.7:

-------------------
4.11.7 - 2019-03-18
-------------------

This change makes a tiny improvement to the core engine's bookkeeping.
There is no user-visible change.

.. _v4.11.6:

-------------------
4.11.6 - 2019-03-15
-------------------

This release changes some of Hypothesis's internal shrinking behaviour in order to reduce memory usage and hopefully improve performance.

.. _v4.11.5:

-------------------
4.11.5 - 2019-03-13
-------------------

This release adds a micro-optimisation to how Hypothesis handles debug reporting internally.
Hard to shrink test may see a slight performance improvement, but in most common scenarios it is unlikely to be noticeable.

.. _v4.11.4:

-------------------
4.11.4 - 2019-03-13
-------------------

This release removes some redundant code that was no longer needed but was still running a significant amount of computation and allocation on the hot path.
This should result in a modest speed improvement for most tests, especially those with large test cases.

.. _v4.11.3:

-------------------
4.11.3 - 2019-03-13
-------------------

This release adds a micro-optimisation to how Hypothesis caches test cases.
This will cause a small improvement in speed and memory usage for large test cases,
but in most common scenarios it is unlikely to be noticeable.

.. _v4.11.2:

-------------------
4.11.2 - 2019-03-13
-------------------

This release removes some internal code that populates a field that is no longer used anywhere.
This should result in some modest performance and speed improvements and no other user visible effects.

.. _v4.11.1:

-------------------
4.11.1 - 2019-03-13
-------------------

This is a formatting-only patch, enabled by a new version of :pypi:`isort`.

.. _v4.11.0:

-------------------
4.11.0 - 2019-03-12
-------------------

This release deprecates :func:`~hypothesis.strategies.sampled_from` with empty
sequences.  This returns :func:`~hypothesis.strategies.nothing`, which gives a
clear error if used directly... but simply vanishes if combined with another
strategy.

Tests that silently generate less than expected are a serious problem for
anyone relying on them to find bugs, and we think reliability more important
than convenience in this case.

.. _v4.10.0:

-------------------
4.10.0 - 2019-03-11
-------------------

This release improves Hypothesis's to detect flaky tests, by noticing when the behaviour of the test changes between runs.
In particular this will notice many new cases where data generation depends on external state (e.g. external sources of randomness) and flag those as flaky sooner and more reliably.

The basis of this feature is a considerable reengineering of how Hypothesis stores its history of test cases,
so on top of this its memory usage should be considerably reduced.

.. _v4.9.0:

------------------
4.9.0 - 2019-03-09
------------------

This release adds the strategy :func:`~hypothesis.extra.numpy.valid_tuple_axes`,
which generates tuples of axis-indices that can be passed to the ``axis`` argument
in NumPy's sequential functions (e.g. :func:`numpy:numpy.sum`).

Thanks to Ryan Soklaski for this strategy.

.. _v4.8.0:

------------------
4.8.0 - 2019-03-06
------------------

This release significantly tightens validation in :class:`hypothesis.settings`.
:obj:`~hypothesis.settings.max_examples`, ``buffer_size``,
and :obj:`~hypothesis.settings.stateful_step_count` must be positive integers;
:obj:`~hypothesis.settings.deadline` must be a positive number or ``None``; and
:obj:`~hypothesis.settings.derandomize` must be either ``True`` or ``False``.

As usual, this replaces existing errors with a more helpful error and starts new
validation checks as deprecation warnings.

.. _v4.7.19:

-------------------
4.7.19 - 2019-03-04
-------------------

This release makes some micro-optimisations to certain calculations performed in the shrinker.
These should particularly speed up large test cases where the shrinker makes many small changes.
It will also reduce the amount allocated, but most of this is garbage that would have been immediately thrown away,
so you probably won't see much effect specifically from that.

.. _v4.7.18:

-------------------
4.7.18 - 2019-03-03
-------------------

This patch removes some overhead from :func:`~hypothesis.extra.numpy.arrays`
with a constant shape and dtype.  The resulting performance improvement is
modest, but worthwile for small arrays.

.. _v4.7.17:

-------------------
4.7.17 - 2019-03-01
-------------------

This release makes some micro-optimisations within Hypothesis's internal representation of test cases.
This should cause heavily nested test cases to allocate less during generation and shrinking,
which should speed things up slightly.

.. _v4.7.16:

-------------------
4.7.16 - 2019-02-28
-------------------

This changes the order in which Hypothesis runs certain operations during shrinking.
This should significantly decrease memory usage and speed up shrinking of large examples.

.. _v4.7.15:

-------------------
4.7.15 - 2019-02-28
-------------------

This release allows Hypothesis to calculate a number of attributes of generated test cases lazily.
This should significantly reduce memory usage and modestly improve performance,
especially for large test cases.

.. _v4.7.14:

-------------------
4.7.14 - 2019-02-28
-------------------

This release reduces the number of operations the shrinker will try when reordering parts of a test case.
This should in some circumstances significantly speed up shrinking. It *may* result in different final test cases,
and if so usually slightly worse ones, but it should not generally have much impact on the end result as the operations removed were typically useless.

.. _v4.7.13:

-------------------
4.7.13 - 2019-02-27
-------------------

This release changes how Hypothesis reorders examples within a test case during shrinking.
This should make shrinking considerably faster.

.. _v4.7.12:

-------------------
4.7.12 - 2019-02-27
-------------------

This release slightly improves the shrinker's ability to replace parts of a test case with their minimal version,
by allowing it to do so in bulk rather than one at a time. Where this is effective, shrinker performance should be modestly improved.

.. _v4.7.11:

-------------------
4.7.11 - 2019-02-25
-------------------

This release makes some micro-optimisations to common operations performed during shrinking.
Shrinking should now be slightly faster, especially for large examples with relatively fast test functions.

.. _v4.7.10:

-------------------
4.7.10 - 2019-02-25
-------------------

This release is a purely internal refactoring of Hypothesis's API for representing test cases.
There should be no user visible effect.

.. _v4.7.9:

------------------
4.7.9 - 2019-02-24
------------------

This release changes certain shrink passes to make them more efficient when
they aren't making progress.

.. _v4.7.8:

------------------
4.7.8 - 2019-02-23
------------------

This patch removes some unused code, which makes the internals
a bit easier to understand.  There is no user-visible impact.

.. _v4.7.7:

------------------
4.7.7 - 2019-02-23
------------------

This release reduces the number of operations the shrinker will try when reordering parts of a test case.
This should in some circumstances significantly speed up shrinking. It *may* result in different final test cases,
and if so usually slightly worse ones, but it should not generally have much impact on the end result as the operations removed were typically useless.

.. _v4.7.6:

------------------
4.7.6 - 2019-02-23
------------------

This patch removes some unused code from the shrinker.
There is no user-visible change.

.. _v4.7.5:

------------------
4.7.5 - 2019-02-23
------------------

This release changes certain shrink passes to make them *adaptive* - that is,
in cases where they are successfully making progress they may now do so significantly
faster.

.. _v4.7.4:

------------------
4.7.4 - 2019-02-22
------------------

This is a docs-only patch, noting that because the :pypi:`lark-parser` is under active
development at version 0.x, ``hypothesis[lark]`` APIs may break in minor
releases if necessary to keep up with the upstream package.

.. _v4.7.3:

------------------
4.7.3 - 2019-02-22
------------------

This changes Hypothesis to no longer import various test frameworks by default (if they are installed).
which will speed up the initial ``import hypothesis`` call.

.. _v4.7.2:

------------------
4.7.2 - 2019-02-22
------------------

This release changes Hypothesis's internal representation of a test case to calculate some expensive structural information on demand rather than eagerly.
This should reduce memory usage a fair bit, and may make generation somewhat faster.

.. _v4.7.1:

------------------
4.7.1 - 2019-02-21
------------------

This release refactors the internal representation of previously run test cases.
The main thing you should see as a result is that Hypothesis becomes somewhat less memory hungry.

.. _v4.7.0:

------------------
4.7.0 - 2019-02-21
------------------

This patch allows :func:`~hypothesis.extra.numpy.array_shapes` to generate shapes
with side-length or even dimension zero, though the minimum still defaults to
one.  These shapes are rare and have some odd behavior, but are particularly
important to test for just that reason!

In a related bigfix, :func:`~hypothesis.extra.numpy.arrays` now supports generating
zero-dimensional arrays with `dtype=object` and a strategy for iterable elements.
Previously, the array element would incorrectly be set to the first item in the
generated iterable.

Thanks to Ryan Turner for continuing to improve our Numpy support.

.. _v4.6.1:

------------------
4.6.1 - 2019-02-19
------------------

This release is a trivial micro-optimisation inside Hypothesis which should result in it using significantly less memory.

.. _v4.6.0:

------------------
4.6.0 - 2019-02-18
------------------

This release changes some inconsistent behavior of :func:`~hypothesis.extra.numpy.arrays`
from the Numpy extra when asked for an array of ``shape=()``.
:func:`~hypothesis.extra.numpy.arrays` will now always return a Numpy
:class:`~numpy:numpy.ndarray`, and the array will always be of the requested dtype.

Thanks to Ryan Turner for this change.

.. _v4.5.12:

-------------------
4.5.12 - 2019-02-18
-------------------

This release fixes a minor typo in an internal comment. There is no user-visible change.

.. _v4.5.11:

-------------------
4.5.11 - 2019-02-15
-------------------

This release fixes :issue:`1813`, a bug introduced in :ref:`3.59.1 <v3.59.1>`,
which caused :py:meth:`~hypothesis.strategies.random_module` to no longer affect the body of the test:
Although Hypothesis would claim to be seeding the random module in fact tests would always run with a seed of zero.

.. _v4.5.10:

-------------------
4.5.10 - 2019-02-14
-------------------

This patch fixes an off-by-one error in the maximum length of :func:`~hypothesis.strategies.emails`.
Thanks to Krzysztof Jurewicz for :pull:`1812`.

.. _v4.5.9:

------------------
4.5.9 - 2019-02-14
------------------

This patch removes some unused code from the shrinker.
There is no user-visible change.

.. _v4.5.8:

------------------
4.5.8 - 2019-02-12
------------------

This release fixes an internal ``IndexError`` in Hypothesis that could sometimes be triggered during shrinking.

.. _v4.5.7:

------------------
4.5.7 - 2019-02-11
------------------

This release modifies the shrinker to interleave different types of reduction operations,
e.g. switching between deleting data and lowering scalar values rather than trying entirely deletions then entirely lowering.

This may slow things down somewhat in the typical case, but has the major advantage that many previously difficult to shrink examples should become much faster,
because the shrinker will no longer tend to stall when trying some ineffective changes to the shrink target but will instead interleave it with other more effective operations.

.. _v4.5.6:

------------------
4.5.6 - 2019-02-11
------------------

This release makes a number of internal changes to the implementation of :func:`hypothesis.extra.lark.from_lark`.
These are primarily intended as a refactoring, but you may see some minor improvements to performance when generating large strings,
and possibly to shrink quality.

.. _v4.5.5:

------------------
4.5.5 - 2019-02-10
------------------

This patch prints an explanatory note when :issue:`1798` is triggered,
because the error message from Numpy is too terse to locate the problem.

.. _v4.5.4:

------------------
4.5.4 - 2019-02-08
------------------

In Python 2, ``long`` integers are not allowed in the shape argument to
:func:`~hypothesis.extra.numpy.arrays`.  Thanks to Ryan Turner for fixing this.

.. _v4.5.3:

------------------
4.5.3 - 2019-02-08
------------------

This release makes a small internal refactoring to clarify how Hypothesis
instructs tests to stop running when appropriate. There is no user-visible
change.

.. _v4.5.2:

------------------
4.5.2 - 2019-02-06
------------------

This release standardises all of the shrinker's internal operations on running in a random order.

The main effect you will see from this that it should now be much less common for the shrinker to stall for a long time before making further progress.
In some cases this will correspond to shrinking more slowly, but on average it should result in faster shrinking.

.. _v4.5.1:

------------------
4.5.1 - 2019-02-05
------------------

This patch updates some docstrings, but has no runtime changes.

.. _v4.5.0:

------------------
4.5.0 - 2019-02-03
------------------

This release adds ``exclude_min`` and ``exclude_max`` arguments to
:func:`~hypothesis.strategies.floats`, so that you can easily generate values from
`open or half-open intervals <https://en.wikipedia.org/wiki/Interval_(mathematics)>`_
(:issue:`1622`).

.. _v4.4.6:

------------------
4.4.6 - 2019-02-03
------------------

This patch fixes a bug where :func:`~hypothesis.strategies.from_regex`
could throw an internal error if the :obj:`python:re.IGNORECASE` flag
was used (:issue:`1786`).

.. _v4.4.5:

------------------
4.4.5 - 2019-02-02
------------------

This release removes two shrink passes that Hypothesis runs late in the process.
These were very expensive when the test function was slow and often didn't do anything useful.

Shrinking should get faster for most failing tests.
If you see any regression in example quality as a result of this release, please let us know.

.. _v4.4.4:

------------------
4.4.4 - 2019-02-02
------------------

This release modifies the way that Hypothesis deletes data during shrinking.
It will primarily be noticeable for very large examples, which should now shrink faster.

The shrinker is now also able to perform some deletions that it could not previously,
but this is unlikely to be very noticeable.

.. _v4.4.3:

------------------
4.4.3 - 2019-01-25
------------------

This release fixes an open file leak that used to cause ``ResourceWarning``\ s.

.. _v4.4.2:

------------------
4.4.2 - 2019-01-24
------------------

This release changes Hypothesis's internal approach to caching the results of executing test cases.
The result should be that it is now significantly less memory hungry, especially when shrinking large test cases.

Some tests may get slower or faster depending on whether the new or old caching strategy was well suited to them,
but any change in speed in either direction should be minor.

.. _v4.4.1:

------------------
4.4.1 - 2019-01-24
------------------

This patch tightens up some of our internal heuristics to deal with shrinking floating point numbers,
which will now run in fewer circumstances.

You are fairly unlikely to see much difference from this, but if you do you are likely to see shrinking become slightly faster and/or producing slightly worse results.

.. _v4.4.0:

------------------
4.4.0 - 2019-01-24
------------------

This release adds the :func:`~hypothesis.extra.django.from_form` function, which allows automatic testing against Django forms. (:issue:`35`)

Thanks to Paul Stiverson for this feature, which resolves our oldest open issue!

.. _v4.3.0:

------------------
4.3.0 - 2019-01-24
------------------

This release deprecates ``HealthCheck.hung_test`` and disables the
associated runtime check for tests that ran for more than five minutes.
Such a check is redundant now that we enforce the ``deadline`` and
``max_examples`` setting, which can be adjusted independently.

.. _v4.2.0:

------------------
4.2.0 - 2019-01-23
------------------

This release adds a new module, ``hypothesis.extra.lark``, which you
can use to generate strings matching a context-free grammar.

In this initial version, only :pypi:`lark-parser` EBNF grammars are supported,
by the new :func:`hypothesis.extra.lark.from_lark` function.

.. _v4.1.2:

------------------
4.1.2 - 2019-01-23
------------------

This patch fixes a very rare overflow bug (:issue:`1748`) which could raise an
``InvalidArgument`` error in :func:`~hypothesis.strategies.complex_numbers`
even though the arguments were valid.

.. _v4.1.1:

------------------
4.1.1 - 2019-01-23
------------------

This release makes some improvements to internal code organisation and documentation and has no impact on behaviour.

.. _v4.1.0:

------------------
4.1.0 - 2019-01-22
------------------

This release adds :func:`~hypothesis.register_random`, which registers
``random.Random`` instances or compatible objects to be seeded and reset
by Hypothesis to ensure that test cases are deterministic.

We still recommend explicitly passing a ``random.Random`` instance from
:func:`~hypothesis.strategies.randoms` if possible, but registering a
framework-global state for Hypothesis to manage is better than flaky tests!

.. _v4.0.2:

------------------
4.0.2 - 2019-01-22
------------------

This patch fixes :issue:`1387`, where bounded :func:`~hypothesis.strategies.integers`
with a very large range would almost always generate very large numbers.
Now, we usually use the same tuned distribution as unbounded
:func:`~hypothesis.strategies.integers`.

.. _v4.0.1:

------------------
4.0.1 - 2019-01-16
------------------

This release randomizes the order in which the shrinker tries some of its initial normalization operations.
You are unlikely to see much difference as a result unless your generated examples are very large.
In this case you may see some performance improvements in shrinking.

.. _v4.0.0:

------------------
4.0.0 - 2019-01-14
------------------

Welcome to the next major version of Hypothesis!

There are no new features here, as we release those in minor versions.
Instead, 4.0 is a chance for us to remove deprecated features (many already
converted into no-ops), and turn a variety of warnings into errors.

If you were running on the last version of Hypothesis 3.x *without any
Hypothesis deprecation warnings* (or using private APIs), this will be
a very boring upgrade.  **In fact, nothing will change for you at all.**
Per :ref:`our deprecation policy <deprecation-policy>`, warnings added in
the last six months (after 2018-07-05) have not been converted to errors.


Removals
~~~~~~~~
- ``hypothesis.extra.datetime`` has been removed, replaced by the core
  date and time strategies.
- ``hypothesis.extra.fakefactory`` has been removed, replaced by general
  expansion of Hypothesis' strategies and the third-party ecosystem.
- The SQLite example database backend has been removed.

Settings
~~~~~~~~
- The :obj:`~hypothesis.settings.deadline` is now enforced by default, rather than just
  emitting a warning when the default (200 milliseconds per test case) deadline is exceeded.
- The ``database_file`` setting has been removed; use :obj:`~hypothesis.settings.database`.
- The ``perform_health_check`` setting has been removed; use
  :obj:`~hypothesis.settings.suppress_health_check`.
- The ``max_shrinks`` setting has been removed; use :obj:`~hypothesis.settings.phases`
  to disable shrinking.
- The ``min_satisfying_examples``, ``max_iterations``, ``strict``, ``timeout``, and
  ``use_coverage`` settings have been removed without user-configurable replacements.

Strategies
~~~~~~~~~~
- The ``elements`` argument is now required for collection strategies.
- The ``average_size`` argument was a no-op and has been removed.
- Date and time strategies now only accept ``min_value`` and ``max_value`` for bounds.
- :func:`~hypothesis.strategies.builds` now requires that the thing to build is
  passed as the first positional argument.
- Alphabet validation for :func:`~hypothesis.strategies.text` raises errors, not warnings,
  as does category validation for :func:`~hypothesis.strategies.characters`.
- The ``choices()`` strategy has been removed.  Instead, you can use
  :func:`~hypothesis.strategies.data` with :func:`~hypothesis.strategies.sampled_from`,
  so ``choice(elements)`` becomes ``data.draw(sampled_from(elements))``.
- The ``streaming()`` strategy has been removed.  Instead, you can use
  :func:`~hypothesis.strategies.data` and replace iterating over the stream with
  ``data.draw()`` calls.
- :func:`~hypothesis.strategies.sampled_from` and :func:`~hypothesis.strategies.permutations`
  raise errors instead of warnings if passed a collection that is not a sequence.

Miscellaneous
~~~~~~~~~~~~~
- Applying :func:`@given <hypothesis.given>` to a test function multiple times
  was really inefficient, and now it's also an error.
- Using the ``.example()`` method of a strategy (intended for interactive
  exploration) within another strategy or a test function always weakened
  data generation and broke shrinking, and now it's an error too.
- The ``HYPOTHESIS_DATABASE_FILE`` environment variable is no longer
  supported, as the ``database_file`` setting has been removed.
- The ``HYPOTHESIS_VERBOSITY_LEVEL`` environment variable is no longer
  supported.  You can use the ``--hypothesis-verbosity`` pytest argument instead,
  or write your own setup code using the settings profile system to replace it.
- Using :func:`@seed <hypothesis.seed>` or
  :obj:`derandomize=True <hypothesis.settings.derandomize>` now forces
  :obj:`database=None <hypothesis.settings.database>` to ensure results
  are in fact reproducible.  If :obj:`~hypothesis.settings.database` is
  *not* ``None``, doing so also emits a ``HypothesisWarning``.
- Unused exception types have been removed from ``hypothesis.errors``;
  namely ``AbnormalExit``, ``BadData``, ``BadTemplateDraw``,
  ``DefinitelyNoSuchExample``, ``Timeout``, and ``WrongFormat``.

.. _v3.88.3:

-------------------
3.88.3 - 2019-01-11
-------------------

This changes the order that the shrinker tries certain operations in its "emergency" phase which runs late in the process.
The new order should be better at avoiding long stalls where the shrinker is failing to make progress,
which may be helpful if you have difficult to shrink test cases.
However this will not be noticeable in the vast majority of use cases.

.. _v3.88.2:

-------------------
3.88.2 - 2019-01-11
-------------------

This is a pure refactoring release that extracts some logic from the core Hypothesis engine
into its own class and file. It should have no user visible impact.

.. _v3.88.1:

-------------------
3.88.1 - 2019-01-11
-------------------

This patch fixes some markup in our documentation.

.. _v3.88.0:

-------------------
3.88.0 - 2019-01-10
-------------------

Introduces :func:`hypothesis.stateful.multiple`, which allows rules in rule
based state machines to send multiple results at once to their target Bundle,
or none at all.

.. _v3.87.0:

-------------------
3.87.0 - 2019-01-10
-------------------

This release contains a massive cleanup of the Hypothesis for Django extra:

- ``hypothesis.extra.django.models.models()`` is deprecated in favor of
  :func:`hypothesis.extra.django.from_model`.
- ``hypothesis.extra.django.models.add_default_field_mapping()`` is deprecated
  in favor of :func:`hypothesis.extra.django.register_field_strategy`.
- :func:`~hypothesis.extra.django.from_model` does not infer a strategy for
  nullable fields or fields with a default unless passed ``infer``, like
  :func:`~hypothesis.strategies.builds`.
  ``models.models()`` would usually but not always infer, and a special
  ``default_value`` marker object was required to disable inference.

.. _v3.86.9:

-------------------
3.86.9 - 2019-01-09
-------------------

This release improves some internal logic about when a test case in Hypothesis's internal representation could lead to a valid test case.
In some circumstances this can lead to a significant speed up during shrinking.
It may have some minor negative impact on the quality of the final result due to certain shrink passes now having access to less information about test cases in some circumstances, but this should rarely matter.

.. _v3.86.8:

-------------------
3.86.8 - 2019-01-09
-------------------

This release has no user visible changes but updates our URLs to use HTTPS.

.. _v3.86.7:

-------------------
3.86.7 - 2019-01-08
-------------------

Hypothesis can now automatically generate values for Django models with a
`URLfield`, thanks to a new provisional strategy for URLs (:issue:`1388`).

.. _v3.86.6:

-------------------
3.86.6 - 2019-01-07
-------------------

This release is a pure refactoring that extracts some internal code into its own file.
It should have no user visible effect.

.. _v3.86.5:

-------------------
3.86.5 - 2019-01-06
-------------------

This is a docs-only patch, which fixes some typos and removes a few hyperlinks
for deprecated features.

.. _v3.86.4:

-------------------
3.86.4 - 2019-01-04
-------------------

This release changes the order in which the shrinker tries to delete data.
For large and slow tests this may significantly improve the performance of shrinking.

.. _v3.86.3:

-------------------
3.86.3 - 2019-01-04
-------------------

This release fixes a bug where certain places Hypothesis internal errors could be
raised during shrinking when a user exception occurred that suppressed an exception
Hypothesis uses internally in its generation.

The two known ways to trigger this problem were:

* Errors raised in stateful tests' teardown function.
* Errors raised in finally blocks that wrapped a call to ``data.draw``.

These cases will now be handled correctly.

.. _v3.86.2:

-------------------
3.86.2 - 2019-01-04
-------------------

This patch is a docs-only change to fix a broken hyperlink.

.. _v3.86.1:

-------------------
3.86.1 - 2019-01-04
-------------------

This patch fixes :issue:`1732`, where :func:`~hypothesis.strategies.integers`
would always return ``long`` values on Python 2.

.. _v3.86.0:

-------------------
3.86.0 - 2019-01-03
-------------------

This release ensures that infinite numbers are never generated by
:func:`~hypothesis.strategies.floats` with ``allow_infinity=False``,
which could previously happen in some cases where one bound was also
provided.

The trivially inconsistent ``min_value=inf, allow_infinity=False`` now
raises an InvalidArgumentError, as does the inverse with ``max_value``.
You can still use :func:`just(inf) <hypothesis.strategies.just>` to
generate ``inf`` without violating other constraints.

.. _v3.85.3:

-------------------
3.85.3 - 2019-01-02
-------------------

Happy new year everyone!
This release has no user visible changes but updates our copyright headers to include 2019.

.. _v3.85.2:

-------------------
3.85.2 - 2018-12-31
-------------------

This release makes a small change to the way the shrinker works.
You may see some improvements to speed of shrinking on especially large and hard to shrink examples,
but most users are unlikely to see much difference.

.. _v3.85.1:

-------------------
3.85.1 - 2018-12-30
-------------------

This patch fixes :issue:`1700`, where a line that contained a Unicode character
before a lambda definition would cause an internal exception.

.. _v3.85.0:

-------------------
3.85.0 - 2018-12-29
-------------------

Introduces the :func:`hypothesis.stateful.consumes` function. When defining
a rule in stateful testing, it can be used to mark bundles from which values
should be consumed, i. e. removed after use in the rule. This has been
proposed in :issue:`136`.

Thanks to Jochen Müller for this long-awaited feature.

.. _v3.84.6:

-------------------
3.84.6 - 2018-12-28
-------------------

This patch makes a small internal change to fix an issue in Hypothesis's
own coverage tests (:issue:`1718`).

There is no user-visible change.

.. _v3.84.5:

-------------------
3.84.5 - 2018-12-21
-------------------

This patch refactors the ``hypothesis.strategies`` module, so that private
names should no longer appear in tab-completion lists.  We previously relied
on ``__all__`` for this, but not all editors respect it.

.. _v3.84.4:

-------------------
3.84.4 - 2018-12-21
-------------------

This is a follow-up patch to ensure that the deprecation date is automatically
recorded for any new deprecations.  There is no user-visible effect.

.. _v3.84.3:

-------------------
3.84.3 - 2018-12-20
-------------------

This patch updates the Hypothesis pytest plugin to avoid a recently
deprecated hook interface.  There is no user-visible change.

.. _v3.84.2:

-------------------
3.84.2 - 2018-12-19
-------------------

This patch fixes the internals for :func:`~hypothesis.strategies.integers`
with one bound.  Values from this strategy now always shrink towards zero
instead of towards the bound, and should shrink much more efficiently too.
On Python 2, providing a bound incorrectly excluded ``long`` integers,
which can now be generated.

.. _v3.84.1:

-------------------
3.84.1 - 2018-12-18
-------------------

This patch adds information about when features were deprecated, but this
is only recorded internally and has no user-visible effect.

.. _v3.84.0:

-------------------
3.84.0 - 2018-12-18
-------------------

This release changes the stateful testing backend from
``find()`` to use :func:`@given <hypothesis.given>`
(:issue:`1300`).  This doesn't change how you create stateful tests,
but does make them run more like other Hypothesis tests.

:func:`@reproduce_failure <hypothesis.reproduce_failure>` and
:func:`@seed <hypothesis.seed>` now work for stateful tests.

Stateful tests now respect the :attr:`~hypothesis.settings.deadline`
and :attr:`~hypothesis.settings.suppress_health_check` settings,
though they are disabled by default.  You can enable them by using
:func:`@settings(...) <hypothesis.settings>` as a class decorator
with whatever arguments you prefer.

.. _v3.83.2:

-------------------
3.83.2 - 2018-12-17
-------------------

Hypothesis has adopted :pypi:`Black` as our code formatter (:issue:`1686`).
There are no functional changes to the source, but it's prettier!

.. _v3.83.1:

-------------------
3.83.1 - 2018-12-13
-------------------

This patch increases the variety of examples generated by
:func:`~hypothesis.strategies.from_type`.

.. _v3.83.0:

-------------------
3.83.0 - 2018-12-12
-------------------

Our pytest plugin now warns you when strategy functions have been collected
as tests, which may happen when e.g. using the
:func:`@composite <hypothesis.strategies.composite>` decorator when you
should be using ``@given(st.data())`` for inline draws.
Such functions *always* pass when treated as tests, because the lazy creation
of strategies mean that the function body is never actually executed!

.. _v3.82.6:

-------------------
3.82.6 - 2018-12-11
-------------------

Hypothesis can now :ref:`show statistics <statistics>` when running
under :pypi:`pytest-xdist`.  Previously, statistics were only reported
when all tests were run in a single process (:issue:`700`).

.. _v3.82.5:

-------------------
3.82.5 - 2018-12-08
-------------------

This patch fixes :issue:`1667`, where passing bounds of Numpy
dtype ``int64`` to :func:`~hypothesis.strategies.integers` could
cause errors on Python 3 due to internal rounding.

.. _v3.82.4:

-------------------
3.82.4 - 2018-12-08
-------------------

Hypothesis now seeds and resets the global state of
:mod:`np.random <numpy:numpy.random>` for each
test case, to ensure that tests are reproducible.

This matches and complements the existing handling of the
:mod:`python:random` module - Numpy simply maintains an
independent PRNG for performance reasons.

.. _v3.82.3:

-------------------
3.82.3 - 2018-12-08
-------------------

This is a no-op release to add the new ``Framework :: Hypothesis``
`trove classifier <https://pypi.org/classifiers/>`_ to
:pypi:`hypothesis` on PyPI.

You can `use it as a filter <https://pypi.org/search/?c=Framework+%3A%3A+Hypothesis>`_
to find Hypothesis-related packages such as extensions as they add the tag
over the coming weeks, or simply visit :doc:`our curated list <strategies>`.

.. _v3.82.2:

-------------------
3.82.2 - 2018-12-08
-------------------

The :ref:`Hypothesis for Pandas extension <hypothesis-pandas>` is now
listed in ``setup.py``, so you can ``pip install hypothesis[pandas]``.
Thanks to jmshi for this contribution.

.. _v3.82.1:

-------------------
3.82.1 - 2018-10-29
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` on Python 2
for classes where ``cls.__init__ is object.__init__``.
Thanks to ccxcz for reporting :issue:`1656`.

.. _v3.82.0:

-------------------
3.82.0 - 2018-10-29
-------------------

The ``alphabet`` argument for :func:`~hypothesis.strategies.text` now
uses its default value of ``characters(blacklist_categories=('Cs',))``
directly, instead of hiding that behind ``alphabet=None`` and replacing
it within the function.  Passing ``None`` is therefore deprecated.

.. _v3.81.0:

-------------------
3.81.0 - 2018-10-27
-------------------

:class:`~hypothesis.stateful.GenericStateMachine` and
:class:`~hypothesis.stateful.RuleBasedStateMachine` now raise an explicit error
when instances of :obj:`~hypothesis.settings` are assigned to the classes'
settings attribute, which is a no-op (:issue:`1643`). Instead assign to
``SomeStateMachine.TestCase.settings``, or use ``@settings(...)`` as a class
decorator to handle this automatically.

.. _v3.80.0:

-------------------
3.80.0 - 2018-10-25
-------------------

Since :ref:`version 3.68.0 <v3.68.0>`, :func:`~hypothesis.extra.numpy.arrays`
checks that values drawn from the ``elements`` and ``fill`` strategies can be
safely cast to the dtype of the array, and emits a warning otherwise.

This release expands the checks to cover overflow for finite ``complex64``
elements and string truncation caused by too-long elements or trailing null
characters (:issue:`1591`).

.. _v3.79.4:

-------------------
3.79.4 - 2018-10-25
-------------------

Tests using :func:`@given <hypothesis.given>` now shrink errors raised from
:pypi:`pytest` helper functions, instead of reporting the first example found.

This was previously fixed in :ref:`version 3.56.0 <v3.56.0>`, but only for
stateful testing.

.. _v3.79.3:

-------------------
3.79.3 - 2018-10-23
-------------------

Traceback elision is now disabled on Python 2, to avoid an import-time
:class:`python:SyntaxError` under Python < 2.7.9 (Python: :bpo:`21591`,
:ref:`Hypothesis 3.79.2 <v3.79.2>`: :issue:`1648`).

We encourage all users to `upgrade to Python 3 before the end of 2019
<https://pythonclock.org/>`_.

.. _v3.79.2:

-------------------
3.79.2 - 2018-10-23
-------------------

This patch shortens tracebacks from Hypothesis, so you can see exactly
happened in your code without having to skip over irrelevant details
about our internals (:issue:`848`).

In the example test (see :pull:`1582`), this reduces tracebacks from
nine frames to just three - and for a test with multiple errors, from
seven frames per error to just one!

If you *do* want to see the internal details, you can disable frame
elision by setting :obj:`~hypothesis.settings.verbosity` to ``debug``.

.. _v3.79.1:

-------------------
3.79.1 - 2018-10-22
-------------------

The abstract number classes :class:`~python:numbers.Number`,
:class:`~python:numbers.Complex`, :class:`~python:numbers.Real`,
:class:`~python:numbers.Rational`, and :class:`~python:numbers.Integral`
are now supported by the :func:`~hypothesis.strategies.from_type`
strategy.  Previously, you would have to use
:func:`~hypothesis.strategies.register_type_strategy` before they
could be resolved (:issue:`1636`)

.. _v3.79.0:

-------------------
3.79.0 - 2018-10-18
-------------------

This release adds a CLI flag for verbosity ``--hypothesis-verbosity`` to
the Hypothesis pytest plugin, applied after loading the profile specified by
``--hypothesis-profile``. Valid options are the names of verbosity settings,
quiet, normal, verbose or debug.

Thanks to Bex Dunn for writing this patch at the PyCon Australia
sprints!

The pytest header now correctly reports the current profile if
``--hypothesis-profile`` has been used.

Thanks to Mathieu Paturel for the contribution at the Canberra Python
Hacktoberfest.

.. _v3.78.0:

-------------------
3.78.0 - 2018-10-16
-------------------

This release has deprecated the generation of integers, floats and fractions
when the conversion of the upper and/ or lower bound is not 100% exact, e.g.
when an integer gets passed a bound that is not a whole number. (:issue:`1625`)

Thanks to Felix Grünewald for this patch during Hacktoberfest 2018.

.. _v3.77.0:

-------------------
3.77.0 - 2018-10-16
-------------------

This minor release adds functionality to :obj:`~hypothesis.settings` allowing
it to be used as a decorator on :obj:`~hypothesis.stateful.RuleBasedStateMachine`
and :obj:`~hypothesis.stateful.GenericStateMachine`.

Thanks to Tyler Nickerson for this feature in #hacktoberfest!

.. _v3.76.1:

-------------------
3.76.1 - 2018-10-16
-------------------

This patch fixes some warnings added by recent releases of
:pypi:`pydocstyle` and :pypi:`mypy`.

.. _v3.76.0:

-------------------
3.76.0 - 2018-10-11
-------------------

This release deprecates using floats for ``min_size`` and ``max_size``.

The type hint for ``average_size`` arguments has been changed from
``Optional[int]`` to None, because non-None values are always ignored and
deprecated.

.. _v3.75.4:

-------------------
3.75.4 - 2018-10-10
-------------------

This patch adds more internal comments to the core engine's sequence-length
shrinker. There should be no user-visible change.

.. _v3.75.3:

-------------------
3.75.3 - 2018-10-09
-------------------

This patch adds additional comments to some of the core engine's internal
data structures. There is no user-visible change.

.. _v3.75.2:

-------------------
3.75.2 - 2018-10-09
-------------------

This patch avoids caching a trivial case, fixing :issue:`493`.

.. _v3.75.1:

-------------------
3.75.1 - 2018-10-09
-------------------

This patch fixes a broken link in a docstring.
Thanks to Benjamin Lee for this contribution!

.. _v3.75.0:

-------------------
3.75.0 - 2018-10-08
-------------------

This release deprecates  the use of ``min_size=None``, setting the default
``min_size`` to 0 (:issue:`1618`).

.. _v3.74.3:

-------------------
3.74.3 - 2018-10-08
-------------------

This patch makes some small internal changes to comply with a new lint setting
in the build. There should be no user-visible change.

.. _v3.74.2:

-------------------
3.74.2 - 2018-10-03
-------------------

This patch fixes :issue:`1153`, where time spent reifying a strategy was
also counted in the time spent generating the first example.  Strategies
are now fully constructed and validated before the timer is started.

.. _v3.74.1:

-------------------
3.74.1 - 2018-10-03
-------------------

This patch fixes some broken formatting and links in the documentation.

.. _v3.74.0:

-------------------
3.74.0 - 2018-10-01
-------------------

This release checks that the value of the
:attr:`~hypothesis.settings.print_blob` setting is a
``PrintSettings`` instance.

Being able to specify a boolean value was not intended, and is now deprecated.
In addition, specifying ``True`` will now cause the blob to always be printed,
instead of causing it to be suppressed.

Specifying any value that is not a ``PrintSettings``
or a boolean is now an error.

.. _v3.73.5:

-------------------
3.73.5 - 2018-10-01
-------------------

Changes the documentation for ``hypothesis.strategies.datetimes``, ``hypothesis.strategies.dates``, ``hypothesis.strategies.times`` to use the new parameter names ``min_value`` and ``max_value`` instead of the deprecated names

.. _v3.73.4:

-------------------
3.73.4 - 2018-09-30
-------------------

This patch ensures that Hypothesis deprecation warnings display the code
that emitted them when you're not running in ``-Werror`` mode (:issue:`652`).

.. _v3.73.3:

-------------------
3.73.3 - 2018-09-27
-------------------

Tracebacks involving :func:`@composite <hypothesis.strategies.composite>`
are now slightly shorter due to some internal refactoring.

.. _v3.73.2:

-------------------
3.73.2 - 2018-09-26
-------------------

This patch fixes errors in the internal comments for one of the shrinker
passes. There is no user-visible change.

.. _v3.73.1:

-------------------
3.73.1 - 2018-09-25
-------------------

This patch substantially improves the distribution of data generated
with :func:`~hypothesis.strategies.recursive`, and fixes a rare internal
error (:issue:`1502`).

.. _v3.73.0:

-------------------
3.73.0 - 2018-09-24
-------------------

This release adds the :func:`~hypothesis.extra.dpcontracts.fulfill` function,
which is designed for testing code that uses :pypi:`dpcontracts` 0.4 or later
for input validation.  This provides some syntactic sugar around use of
:func:`~hypothesis.assume`, to automatically filter out and retry calls that
cause a precondition check to fail (:issue:`1474`).

.. _v3.72.0:

-------------------
3.72.0 - 2018-09-24
-------------------

This release makes setting attributes of the :class:`hypothesis.settings`
class an explicit error.  This has never had any effect, but could mislead
users who confused it with the current settings *instance*
``hypothesis.settings.default`` (which is also immutable).  You can change
the global settings with :ref:`settings profiles <settings_profiles>`.

.. _v3.71.11:

--------------------
3.71.11 - 2018-09-24
--------------------

This patch factors out some common code in the shrinker for iterating
over pairs of data blocks. There should be no user-visible change.

.. _v3.71.10:

--------------------
3.71.10 - 2018-09-18
--------------------

This patch allows :func:`~hypothesis.strategies.from_type` to handle the
empty tuple type, :obj:`typing.Tuple[()] <python:typing.Tuple>`.

.. _v3.71.9:

-------------------
3.71.9 - 2018-09-17
-------------------

This patch updates some internal comments for :pypi:`mypy`.
There is no user-visible effect, even for Mypy users.

.. _v3.71.8:

-------------------
3.71.8 - 2018-09-17
-------------------

This patch fixes a rare bug that would cause a particular shrinker pass to
raise an IndexError, if a shrink improvement changed the underlying data
in an unexpected way.

.. _v3.71.7:

-------------------
3.71.7 - 2018-09-17
-------------------

This release fixes the broken cross-references in our docs,
and adds a CI check so we don't add new ones.

.. _v3.71.6:

-------------------
3.71.6 - 2018-09-16
-------------------

This patch fixes two bugs (:issue:`944` and :issue:`1521`), where messages
about :func:`@seed <hypothesis.seed>` did not check the current verbosity
setting, and the wrong settings were active while executing
:ref:`explicit examples <providing-explicit-examples>`.

.. _v3.71.5:

-------------------
3.71.5 - 2018-09-15
-------------------

This patch fixes a ``DeprecationWarning`` added in Python 3.8 (:issue:`1576`).

Thanks to tirkarthi for this contribution!

.. _v3.71.4:

-------------------
3.71.4 - 2018-09-14
-------------------

This is a no-op release, which implements automatic DOI minting and code
archival of Hypothesis via `Zenodo <https://zenodo.org/>`_. Thanks to
CERN and the EU *Horizon 2020* programme for providing this service!

Check our :gh-file:`CITATION` file for details, or head right on over to
`doi.org/10.5281/zenodo.1412597 <https://doi.org/10.5281/zenodo.1412597>`_

.. _v3.71.3:

-------------------
3.71.3 - 2018-09-10
-------------------

This release adds the test name to some deprecation warnings,
for easier debugging.

Thanks to Sanyam Khurana for the patch!

.. _v3.71.2:

-------------------
3.71.2 - 2018-09-10
-------------------

This release makes Hypothesis's memory usage substantially smaller for tests with many
examples, by bounding the number of past examples it keeps around.

You will not see much difference unless you are running tests with :obj:`~hypothesis.settings.max_examples`
set to well over ``1000``, but if you do have such tests then you should see memory usage mostly plateau
where previously it would have grown linearly with time.

.. _v3.71.1:

-------------------
3.71.1 - 2018-09-09
-------------------

This patch adds internal comments to some tree traversals in the core engine.
There is no user-visible change.

.. _v3.71.0:

-------------------
3.71.0 - 2018-09-08
-------------------

This release deprecates the coverage-guided testing functionality,
as it has proven brittle and does not really pull its weight.

We intend to replace it with something more useful in the future,
but the feature in its current form does not seem to be worth the cost of using,
and whatever replaces it will likely look very different.

.. _v3.70.4:

-------------------
3.70.4 - 2018-09-08
-------------------

This patch changes the behaviour of :func:`~hypothesis.reproduce_failure`
so that blobs are only printed in quiet mode when the
:obj:`~hypothesis.settings.print_blob` setting is set to ``ALWAYS``.

Thanks to Cameron McGill for writing this patch at the PyCon Australia sprints!

.. _v3.70.3:

-------------------
3.70.3 - 2018-09-03
-------------------

This patch removes some unnecessary code from the internals.
There is no user-visible change.

.. _v3.70.2:

-------------------
3.70.2 - 2018-09-03
-------------------

This patch fixes an internal bug where a corrupted argument to
:func:`@reproduce_failure <hypothesis.reproduce_failure>` could raise
the wrong type of error.  Thanks again to Paweł T. Jochym, who maintains
Hypothesis on `conda-forge <https://conda-forge.org/>`_ and consistently
provides excellent bug reports including :issue:`1558`.

.. _v3.70.1:

-------------------
3.70.1 - 2018-09-03
-------------------

This patch updates hypothesis to report its version and settings when run with
pytest. (:issue:`1223`).

Thanks to Jack Massey for this feature.

.. _v3.70.0:

-------------------
3.70.0 - 2018-09-01
-------------------

This release adds a ``fullmatch`` argument to
:func:`~hypothesis.strategies.from_regex`.  When ``fullmatch=True``, the
whole example will match the regex pattern as for :func:`python:re.fullmatch`.

Thanks to Jakub Nabaglo for writing this patch at the PyCon Australia sprints!

.. _v3.69.12:

--------------------
3.69.12 - 2018-08-30
--------------------

This release reverts the changes to logging handling in 3.69.11,
which broke test that use the :pypi:`pytest` ``caplog`` fixture
internally because all logging was disabled (:issue:`1546`).

.. _v3.69.11:

--------------------
3.69.11 - 2018-08-29
--------------------

This patch will hide all logging messages produced by test cases before the
final, minimal, failing test case (:issue:`356`).

Thanks to Gary Donovan for writing this patch at the PyCon Australia sprints!

.. _v3.69.10:

--------------------
3.69.10 - 2018-08-29
--------------------

This patch fixes a bug that prevents coverage from reporting unexecuted
Python files (:issue:`1085`).

Thanks to Gary Donovan for writing this patch at the PyCon Australia sprints!

.. _v3.69.9:

-------------------
3.69.9 - 2018-08-28
-------------------

This patch improves the packaging of the Python package by adding
``LICENSE.txt`` to the sdist (:issue:`1311`), clarifying the minimum
supported versions of :pypi:`pytz` and :pypi:`dateutil <python-dateutil>`
(:issue:`1383`), and adds keywords to the metadata (:issue:`1520`).

Thanks to Graham Williamson for writing this patch at the PyCon
Australia sprints!

.. _v3.69.8:

-------------------
3.69.8 - 2018-08-28
-------------------

This is an internal change which replaces pickle with json to prevent possible
security issues.

Thanks to Vidya Rani D G for writing this patch at the PyCon Australia sprints!

.. _v3.69.7:

-------------------
3.69.7 - 2018-08-28
-------------------

This patch ensures that :func:`~hypothesis.note` prints the note for every
test case when the :obj:`~hypothesis.settings.verbosity` setting is
``Verbosity.verbose``.  At normal verbosity it only prints from the final
test case.

Thanks to Tom McDermott for writing this patch at
the PyCon Australia sprints!

.. _v3.69.6:

-------------------
3.69.6 - 2018-08-27
-------------------

This patch improves the testing of some internal caching.  It should have
no user-visible effect.

.. _v3.69.5:

-------------------
3.69.5 - 2018-08-27
-------------------

This change performs a small rename and refactoring in the core engine.
There is no user-visible change.

.. _v3.69.4:

-------------------
3.69.4 - 2018-08-27
-------------------

This change improves the core engine's ability to avoid unnecessary work,
by consulting its cache of previously-tried inputs in more cases.

.. _v3.69.3:

-------------------
3.69.3 - 2018-08-27
-------------------

This patch handles passing an empty :class:`python:enum.Enum` to
:func:`~hypothesis.strategies.from_type` by returning
:func:`~hypothesis.strategies.nothing`, instead of raising an
internal :class:`python:AssertionError`.

Thanks to Paul Amazona for writing this patch at the
PyCon Australia sprints!

.. _v3.69.2:

-------------------
3.69.2 - 2018-08-23
-------------------

This patch fixes a small mistake in an internal comment.
There is no user-visible change.

.. _v3.69.1:

-------------------
3.69.1 - 2018-08-21
-------------------

This change fixes a small bug in how the core engine consults its cache
of previously-tried inputs. There is unlikely to be any user-visible change.

.. _v3.69.0:

-------------------
3.69.0 - 2018-08-20
-------------------

This release improves argument validation for stateful testing.

- If the target or targets of a :func:`~hypothesis.stateful.rule` are invalid,
  we now raise a useful validation error rather than an internal exception.
- Passing both the ``target`` and ``targets`` arguments is deprecated -
  append the ``target`` bundle to the ``targets`` tuple of bundles instead.
- Passing the name of a Bundle rather than the Bundle itself is also deprecated.

.. _v3.68.3:

-------------------
3.68.3 - 2018-08-20
-------------------

This is a docs-only patch, fixing some typos and formatting issues.

.. _v3.68.2:

-------------------
3.68.2 - 2018-08-19
-------------------

This change fixes a small bug in how the core engine caches the results of
previously-tried inputs. The effect is unlikely to be noticeable, but it might
avoid unnecesary work in some cases.

.. _v3.68.1:

-------------------
3.68.1 - 2018-08-18
-------------------

This patch documents the :func:`~hypothesis.extra.numpy.from_dtype` function,
which infers a strategy for :class:`numpy:numpy.dtype`\ s.  This is used in
:func:`~hypothesis.extra.numpy.arrays`, but can also be used directly when
creating e.g. Pandas objects.

.. _v3.68.0:

-------------------
3.68.0 - 2018-08-15
-------------------

:func:`~hypothesis.extra.numpy.arrays` now checks that integer and float
values drawn from ``elements`` and ``fill`` strategies can be safely cast
to the dtype of the array, and emits a warning otherwise (:issue:`1385`).

Elements in the resulting array could previously violate constraints on
the elements strategy due to floating-point overflow or truncation of
integers to fit smaller types.

.. _v3.67.1:

-------------------
3.67.1 - 2018-08-14
-------------------

This release contains a tiny refactoring of the internals.
There is no user-visible change.

.. _v3.67.0:

-------------------
3.67.0 - 2018-08-10
-------------------

This release adds a ``width`` argument to :func:`~hypothesis.strategies.floats`,
to generate lower-precision floating point numbers for e.g. Numpy arrays.

The generated examples are always instances of Python's native ``float``
type, which is 64bit, but passing ``width=32`` will ensure that all values
can be exactly represented as 32bit floats.  This can be useful to avoid
overflow (to +/- infinity), and for efficiency of generation and shrinking.

Half-precision floats (``width=16``) are also supported, but require Numpy
if you are running Python 3.5 or earlier.

.. _v3.66.33:

--------------------
3.66.33 - 2018-08-10
--------------------

This release fixes a bug in :func:`~hypothesis.strategies.floats`, where
setting ``allow_infinity=False`` and exactly one of ``min_value`` and
``max_value`` would allow infinite values to be generated.

.. _v3.66.32:

--------------------
3.66.32 - 2018-08-09
--------------------

This release adds type hints to the :func:`~hypothesis.example` and
:func:`~hypothesis.seed` decorators, and fixes the type hint on
:func:`~hypothesis.strategies.register_type_strategy`. The second argument to
:func:`~hypothesis.strategies.register_type_strategy` must either be a
``SearchStrategy``, or a callable which takes a ``type`` and returns a
``SearchStrategy``.

.. _v3.66.31:

--------------------
3.66.31 - 2018-08-08
--------------------

Another set of changes designed to improve the performance of shrinking on
large examples. In particular the shrinker should now spend considerably less
time running useless shrinks.

.. _v3.66.30:

--------------------
3.66.30 - 2018-08-06
--------------------

"Bug fixes and performance improvements".

This release is a fairly major overhaul of the shrinker designed to improve
its behaviour on large examples, especially around stateful testing. You
should hopefully see shrinking become much faster, with little to no quality
degradation (in some cases quality may even improve).

.. _v3.66.29:

--------------------
3.66.29 - 2018-08-05
--------------------

This release fixes two very minor bugs in the core engine:

* it fixes a corner case that was missing in :ref:`3.66.28 <v3.66.28>`, which
  should cause shrinking to work slightly better.
* it fixes some logic for how shrinking interacts with the database that was
  causing Hypothesis to be insufficiently aggressive about clearing out old
  keys.

.. _v3.66.28:

--------------------
3.66.28 - 2018-08-05
--------------------

This release improves how Hypothesis handles reducing the size of integers'
representation. This change should mostly be invisible as it's purely about
the underlying representation and not the generated value, but it may result
in some improvements to shrink performance.

.. _v3.66.27:

--------------------
3.66.27 - 2018-08-05
--------------------

This release changes the order in which Hypothesis chooses parts of the test case
to shrink. For typical usage this should be a significant performance improvement on
large examples. It is unlikely to have a major impact on example quality, but where
it does change the result it should usually be an improvement.

.. _v3.66.26:

--------------------
3.66.26 - 2018-08-05
--------------------

This release improves the debugging information that the shrinker emits about
the operations it performs, giving better summary statistics about which
passes resulted in test executions and whether they were successful.

.. _v3.66.25:

--------------------
3.66.25 - 2018-08-05
--------------------

This release fixes several bugs that were introduced to the shrinker in
:ref:`3.66.24 <v3.66.24>` which would have caused it to behave significantly
less well than advertised. With any luck you should *actually* see the promised
benefits now.

.. _v3.66.24:

--------------------
3.66.24 - 2018-08-03
--------------------

This release changes how Hypothesis deletes data when shrinking in order to
better handle deletion of large numbers of contiguous sequences. Most tests
should see little change, but this will hopefully provide a significant
speed up for :doc:`stateful testing <stateful>`.

.. _v3.66.23:

--------------------
3.66.23 - 2018-08-02
--------------------

This release makes some internal changes to enable further improvements to the
shrinker. You may see some changes in the final shrunk examples, but they are
unlikely to be significant.

.. _v3.66.22:

--------------------
3.66.22 - 2018-08-01
--------------------

This release adds some more internal caching to the shrinker. This should cause
a significant speed up for shrinking, especially for stateful testing and
large example sizes.

.. _v3.66.21:

--------------------
3.66.21 - 2018-08-01
--------------------

This patch is for downstream packagers - our tests now pass under
:pypi:`pytest` 3.7.0 (released 2018-07-30).  There are no changes
to the source of Hypothesis itself.

.. _v3.66.20:

--------------------
3.66.20 - 2018-08-01
--------------------

This release removes some functionality from the shrinker that was taking a
considerable amount of time and does not appear to be useful any more due to
a number of quality improvements in the shrinker.

You may see some degradation in shrink quality as a result of this, but mostly
shrinking should just get much faster.

.. _v3.66.19:

--------------------
3.66.19 - 2018-08-01
--------------------

This release slightly changes the format of some debugging information emitted
during shrinking, and refactors some of the internal interfaces around that.

.. _v3.66.18:

--------------------
3.66.18 - 2018-07-31
--------------------

This release is a very small internal refactoring which should have no user
visible impact.

.. _v3.66.17:

--------------------
3.66.17 - 2018-07-31
--------------------

This release fixes a bug that could cause an ``IndexError`` to be raised from
inside Hypothesis during shrinking. It is likely that it was impossible to
trigger this bug in practice - it was only made visible by some currently
unreleased work.

.. _v3.66.16:

--------------------
3.66.16 - 2018-07-31
--------------------

This release is a very small internal refactoring which should have no user
visible impact.

.. _v3.66.15:

--------------------
3.66.15 - 2018-07-31
--------------------

This release makes Hypothesis's shrinking faster by removing some redundant
work that it does when minimizing values in its internal representation.

.. _v3.66.14:

--------------------
3.66.14 - 2018-07-30
--------------------

This release expands the deprecation of timeout from :ref:`3.16.0 <v3.16.0>` to
also emit the deprecation warning in ``find`` or :doc:`stateful testing <stateful>`.

.. _v3.66.13:

--------------------
3.66.13 - 2018-07-30
--------------------

This release adds an additional shrink pass that is able to reduce the size of
examples in some cases where the transformation is non-obvious. In particular
this will improve the quality of some examples which would have regressed in
:ref:`3.66.12 <v3.66.12>`.

.. _v3.66.12:

--------------------
3.66.12 - 2018-07-28
--------------------

This release changes how we group data together for shrinking. It should result
in improved shrinker performance, especially in stateful testing.

.. _v3.66.11:

--------------------
3.66.11 - 2018-07-28
--------------------

This patch modifies how which rule to run is selected during
:doc:`rule based stateful testing <stateful>`. This should result in a slight
performance increase during generation and a significant performance and
quality improvement when shrinking.

As a result of this change, some state machines which would previously have
thrown an ``InvalidDefinition`` are no longer detected as invalid.

.. _v3.66.10:

--------------------
3.66.10 - 2018-07-28
--------------------

This release weakens some minor functionality in the shrinker that had only
modest benefit and made its behaviour much harder to reason about.

This is unlikely to have much user visible effect, but it is possible that in
some cases shrinking may get slightly slower. It is primarily to make it easier
to work on the shrinker and pave the way for future work.

.. _v3.66.9:

-------------------
3.66.9 - 2018-07-26
-------------------

This release improves the information that Hypothesis emits about its shrinking
when :obj:`~hypothesis.settings.verbosity` is set to debug.

.. _v3.66.8:

-------------------
3.66.8 - 2018-07-24
-------------------

This patch includes some minor fixes in the documentation, and updates
the minimum version of :pypi:`pytest` to 3.0 (released August 2016).

.. _v3.66.7:

-------------------
3.66.7 - 2018-07-24
-------------------

This release fixes a bug where difficult to shrink tests could sometimes
trigger an internal assertion error inside the shrinker.

.. _v3.66.6:

-------------------
3.66.6 - 2018-07-23
-------------------

This patch ensures that Hypothesis fully supports Python 3.7, by
upgrading :func:`~hypothesis.strategies.from_type` (:issue:`1264`)
and fixing some minor issues in our test suite (:issue:`1148`).

.. _v3.66.5:

-------------------
3.66.5 - 2018-07-22
-------------------

This patch fixes the online docs for various extras, by ensuring that
their dependencies are installed on readthedocs.io (:issue:`1326`).

.. _v3.66.4:

-------------------
3.66.4 - 2018-07-20
-------------------

This release improves the shrinker's ability to reorder examples.

For example, consider the following test:

.. code-block:: python

    import hypothesis.strategies as st
    from hypothesis import given


    @given(st.text(), st.text())
    def test_non_equal(x, y):
        assert x != y

Previously this could have failed with either of ``x="", y="0"`` or
``x="0", y=""``. Now it should always fail with ``x="", y="0"``.

This will allow the shrinker to produce more consistent results, especially in
cases where test cases contain some ordered collection whose actual order does
not matter.

.. _v3.66.3:

-------------------
3.66.3 - 2018-07-20
-------------------

This patch fixes inference in the :func:`~hypothesis.strategies.builds`
strategy with subtypes of :class:`python:typing.NamedTuple`, where the
``__init__`` method is not useful for introspection.  We now use the
field types instead - thanks to James Uther for identifying this bug.

.. _v3.66.2:

-------------------
3.66.2 - 2018-07-19
-------------------

This release improves the shrinker's ability to handle situations where there
is an additive constraint between two values.

For example, consider the following test:


.. code-block:: python

    import hypothesis.strategies as st
    from hypothesis import given


    @given(st.integers(), st.integers())
    def test_does_not_exceed_100(m, n):
        assert m + n < 100

Previously this could have failed with almost any pair ``(m, n)`` with
``0 <= m <= n`` and ``m + n == 100``. Now it should almost always fail with
``m=0, n=100``.

This is a relatively niche specialisation, but can be useful in situations
where e.g. a bug is triggered by an integer overflow.

.. _v3.66.1:

-------------------
3.66.1 - 2018-07-09
-------------------

This patch fixes a rare bug where an incorrect percentage drawtime
could be displayed for a test, when the system clock was changed during
a test running under Python 2 (we use :func:`python:time.monotonic`
where it is available to avoid such problems).  It also fixes a possible
zero-division error that can occur when the underlying C library
double-rounds an intermediate value in :func:`python:math.fsum` and
gets the least significant bit wrong.

.. _v3.66.0:

-------------------
3.66.0 - 2018-07-05
-------------------

This release improves validation of the ``alphabet`` argument to the
:func:`~hypothesis.strategies.text` strategy.  The following misuses
are now deprecated, and will be an error in a future version:

- passing an unordered collection (such as ``set('abc')``), which
  violates invariants about shrinking and reproducibility
- passing an alphabet sequence with elements that are not strings
- passing an alphabet sequence with elements that are not of length one,
  which violates any size constraints that may apply

Thanks to Sushobhit for adding these warnings (:issue:`1329`).

.. _v3.65.3:

-------------------
3.65.3 - 2018-07-04
-------------------

This release fixes a mostly theoretical bug where certain usage of the internal
API could trigger an assertion error inside Hypothesis. It is unlikely that
this problem is even possible to trigger through the public API.

.. _v3.65.2:

-------------------
3.65.2 - 2018-07-04
-------------------

This release fixes dependency information for coverage.  Previously Hypothesis
would allow installing :pypi:`coverage` with any version, but it only works
with coverage 4.0 or later.

We now specify the correct metadata in our ``setup.py``, so Hypothesis will
only allow installation with compatible versions of coverage.

.. _v3.65.1:

-------------------
3.65.1 - 2018-07-03
-------------------

This patch ensures that :doc:`stateful tests <stateful>` which raise an
error from a :pypi:`pytest` helper still print the sequence of steps
taken to reach that point (:issue:`1372`).  This reporting was previously
broken because the helpers inherit directly from :class:`python:BaseException`, and
therefore require special handling to catch without breaking e.g. the use
of ctrl-C to quit the test.

.. _v3.65.0:

-------------------
3.65.0 - 2018-06-30
-------------------

This release deprecates the ``max_shrinks`` setting
in favor of an internal heuristic.  If you need to avoid shrinking examples,
use the :obj:`~hypothesis.settings.phases` setting instead.  (:issue:`1235`)

.. _v3.64.2:

-------------------
3.64.2 - 2018-06-27
-------------------

This release fixes a bug where an internal assertion error could sometimes be
triggered while shrinking a failing test.

.. _v3.64.1:

-------------------
3.64.1 - 2018-06-27
-------------------

This patch fixes type-checking errors in our vendored pretty-printer,
which were ignored by our mypy config but visible for anyone else
(whoops).  Thanks to Pi Delport for reporting :issue:`1359` so promptly.

.. _v3.64.0:

-------------------
3.64.0 - 2018-06-26
-------------------

This release adds :ref:`an interface <custom-function-execution>`
which can be used to insert a wrapper between the original test function and
:func:`@given <hypothesis.given>` (:issue:`1257`).  This will be particularly
useful for test runner extensions such as :pypi:`pytest-trio`, but is
not recommended for direct use by other users of Hypothesis.

.. _v3.63.0:

-------------------
3.63.0 - 2018-06-26
-------------------

This release adds a new mechanism to infer strategies for classes
defined using :pypi:`attrs`, based on the the type, converter, or
validator of each attribute.  This inference is now built in to
:func:`~hypothesis.strategies.builds` and :func:`~hypothesis.strategies.from_type`.

On Python 2, :func:`~hypothesis.strategies.from_type` no longer generates
instances of ``int`` when passed ``long``, or vice-versa.

.. _v3.62.0:

-------------------
3.62.0 - 2018-06-26
-------------------

This release adds :PEP:`484` type hints to Hypothesis on a provisional
basis, using the comment-based syntax for Python 2 compatibility.  You
can :ref:`read more about our type hints here <our-type-hints>`.

It *also* adds the ``py.typed`` marker specified in :PEP:`561`.
After you ``pip install hypothesis``, :pypi:`mypy` 0.590 or later
will therefore type-check your use of our public interface!

.. _v3.61.0:

-------------------
3.61.0 - 2018-06-24
-------------------

This release deprecates the use of :class:`~hypothesis.settings` as a
context manager, the use of which is somewhat ambiguous.

Users should define settings with global state or with the
:func:`@settings(...) <hypothesis.settings>` decorator.

.. _v3.60.1:

-------------------
3.60.1 - 2018-06-20
-------------------

Fixed a bug in generating an instance of a Django model from a
strategy where the primary key is generated as part of the
strategy. See :ref:`details here <django-generating-primary-key>`.

Thanks to Tim Martin for this contribution.

.. _v3.60.0:

-------------------
3.60.0 - 2018-06-20
-------------------

This release adds the :func:`@initialize <hypothesis.stateful.initialize>`
decorator for stateful testing (originally discussed in :issue:`1216`).
All :func:`@initialize <hypothesis.stateful.initialize>` rules will be called
once each in an arbitrary order before any normal rule is called.

.. _v3.59.3:

-------------------
3.59.3 - 2018-06-19
-------------------

This is a no-op release to take into account some changes to the release
process. It should have no user visible effect.

.. _v3.59.2:

-------------------
3.59.2 - 2018-06-18
-------------------

This adds support for partially sorting examples which cannot be fully sorted.
For example, [5, 4, 3, 2, 1, 0] with a constraint that the first element needs
to be larger than the last becomes [1, 2, 3, 4, 5, 0].

Thanks to Luke for contributing.

.. _v3.59.1:

-------------------
3.59.1 - 2018-06-16
-------------------

This patch uses :func:`python:random.getstate` and :func:`python:random.setstate`
to restore the PRNG state after :func:`@given <hypothesis.given>` runs
deterministic tests.  Without restoring state, you might have noticed problems
such as :issue:`1266`.  The fix also applies to stateful testing (:issue:`702`).

.. _v3.59.0:

-------------------
3.59.0 - 2018-06-14
-------------------

This release adds the :func:`~hypothesis.strategies.emails` strategy,
which generates unicode strings representing an email address.

Thanks to Sushobhit for moving this to the public API (:issue:`162`).

.. _v3.58.1:

-------------------
3.58.1 - 2018-06-13
-------------------

This improves the shrinker. It can now reorder examples: 3 1 2 becomes 1 2 3.

Thanks to Luke for contributing.

.. _v3.58.0:

-------------------
3.58.0 - 2018-06-13
-------------------

This adds a new extra :py:func:`~hypothesis.extra.dateutil.timezones` strategy
that generates :pypi:`dateutil timezones <python-dateutil>`.

Thanks to Conrad for contributing.

.. _v3.57.0:

-------------------
3.57.0 - 2018-05-20
-------------------

Using an unordered collection with the :func:`~hypothesis.strategies.permutations`
strategy has been deprecated because the order in which e.g. a set shrinks is
arbitrary. This may cause different results between runs.

.. _v3.56.10:

--------------------
3.56.10 - 2018-05-16
--------------------

This release makes ``hypothesis.settings.define_setting``
a private method, which has the effect of hiding it from the
documentation.

.. _v3.56.9:

-------------------
3.56.9 - 2018-05-11
-------------------

This is another release with no functionality changes as part of changes to
Hypothesis's new release tagging scheme.

.. _v3.56.8:

-------------------
3.56.8 - 2018-05-10
-------------------

This is a release with no functionality changes that moves Hypothesis over to
a new release tagging scheme.

.. _v3.56.7:

-------------------
3.56.7 - 2018-05-10
-------------------

This release provides a performance improvement for most tests, but in
particular users of :func:`~hypothesis.strategies.sampled_from` who don't
have numpy installed should see a significant performance improvement.

.. _v3.56.6:

-------------------
3.56.6 - 2018-05-09
-------------------

This patch contains further internal work to support Mypy.
There are no user-visible changes... yet.

.. _v3.56.5:

-------------------
3.56.5 - 2018-04-22
-------------------

This patch contains some internal refactoring to run :pypi:`mypy` in CI.
There are no user-visible changes.

.. _v3.56.4:

-------------------
3.56.4 - 2018-04-21
-------------------

This release involves some very minor internal clean up and should have no
user visible effect at all.

.. _v3.56.3:

-------------------
3.56.3 - 2018-04-20
-------------------

This release fixes a problem introduced in :ref:`3.56.0 <v3.56.0>` where
setting the hypothesis home directory (through currently undocumented
means) would no longer result in the default database location living
in the new home directory.

.. _v3.56.2:

-------------------
3.56.2 - 2018-04-20
-------------------

This release fixes a problem introduced in :ref:`3.56.0 <v3.56.0>` where
setting :obj:`~hypothesis.settings.max_examples` to ``1`` would result in tests
failing with ``Unsatisfiable``. This problem could also occur in other harder
to trigger circumstances (e.g. by setting it to a low value, having a hard to
satisfy assumption, and disabling health checks).

.. _v3.56.1:

-------------------
3.56.1 - 2018-04-20
-------------------

This release fixes a problem that was introduced in :ref:`3.56.0 <v3.56.0>`:
Use of the ``HYPOTHESIS_VERBOSITY_LEVEL`` environment variable was, rather
than deprecated, actually broken due to being read before various setup
the deprecation path needed was done. It now works correctly (and emits a
deprecation warning).

.. _v3.56.0:

-------------------
3.56.0 - 2018-04-17
-------------------

This release deprecates several redundant or internally oriented
:class:`~hypothesis.settings`, working towards an orthogonal set of
configuration options that are widely useful *without* requiring any
knowledge of our internals (:issue:`535`).

- Deprecated settings that no longer have any effect are no longer
  shown in the ``__repr__`` unless set to a non-default value.
- ``hypothesis.settings.perform_health_check`` is deprecated, as it
  duplicates :obj:`~hypothesis.settings.suppress_health_check`.
- ``hypothesis.settings.max_iterations`` is deprecated and disabled,
  because we can usually get better behaviour from an internal heuristic
  than a user-controlled setting.
- ``hypothesis.settings.min_satisfying_examples`` is deprecated and
  disabled, due to overlap with the
  :obj:`~hypothesis.HealthCheck.filter_too_much` healthcheck
  and poor interaction with :obj:`~hypothesis.settings.max_examples`.
- ``HYPOTHESIS_VERBOSITY_LEVEL`` is now deprecated.  Set
  :obj:`~hypothesis.settings.verbosity` through the profile system instead.
- Examples tried by ``find()`` are now reported at ``debug``
  verbosity level (as well as ``verbose`` level).

.. _v3.55.6:

-------------------
3.55.6 - 2018-04-14
-------------------

This release fixes a somewhat obscure condition (:issue:`1230`) under which you
could occasionally see a failing test trigger an assertion error inside
Hypothesis instead of failing normally.

.. _v3.55.5:

-------------------
3.55.5 - 2018-04-14
-------------------

This patch fixes one possible cause of :issue:`966`.  When running
Python 2 with hash randomisation, passing a :obj:`python:bytes` object
to :func:`python:random.seed` would use ``version=1``, which broke
:obj:`~hypothesis.settings.derandomize` (because the seed depended on
a randomised hash).  If :obj:`~hypothesis.settings.derandomize` is
*still* nondeterministic for you, please open an issue.

.. _v3.55.4:

-------------------
3.55.4 - 2018-04-13
-------------------

This patch makes a variety of minor improvements to the documentation,
and improves a few validation messages for invalid inputs.

.. _v3.55.3:

-------------------
3.55.3 - 2018-04-12
-------------------

This release updates the URL metadata associated with the PyPI package (again).
It has no other user visible effects.

.. _v3.55.2:

-------------------
3.55.2 - 2018-04-11
-------------------

This release updates the URL metadata associated with the PyPI package.
It has no other user visible effects.

.. _v3.55.1:

-------------------
3.55.1 - 2018-04-06
-------------------

This patch relaxes constraints in our tests on the expected values returned
by the standard library function :func:`~python:math.hypot` and the internal
helper function ``cathetus``, to fix near-exact
test failures on some 32-bit systems used by downstream packagers.

.. _v3.55.0:

-------------------
3.55.0 - 2018-04-05
-------------------

This release includes several improvements to the handling of the
:obj:`~hypothesis.settings.database` setting.

- The ``database_file`` setting was a historical
  artefact, and you should just use :obj:`~hypothesis.settings.database`
  directly.
- The ``HYPOTHESIS_DATABASE_FILE`` environment variable is
  deprecated, in favor of :meth:`~hypothesis.settings.load_profile` and
  the :obj:`~hypothesis.settings.database` setting.
- If you have not configured the example database at all and the default
  location is not usable (due to e.g. permissions issues), Hypothesis
  will fall back to an in-memory database.  This is not persisted between
  sessions, but means that the defaults work on read-only filesystems.

.. _v3.54.0:

-------------------
3.54.0 - 2018-04-04
-------------------

This release improves the :func:`~hypothesis.strategies.complex_numbers`
strategy, which now supports ``min_magnitude`` and ``max_magnitude``
arguments, along with ``allow_nan`` and ``allow_infinity`` like for
:func:`~hypothesis.strategies.floats`.

Thanks to J.J. Green for this feature.

.. _v3.53.0:

-------------------
3.53.0 - 2018-04-01
-------------------

This release removes support for Django 1.8, which reached end of life on
2018-04-01.  You can see Django's release and support schedule
`on the Django Project website <https://www.djangoproject.com/download/#supported-versions>`_.

.. _v3.52.3:

-------------------
3.52.3 - 2018-04-01
-------------------

This patch fixes the ``min_satisfying_examples`` settings
documentation, by explaining that example shrinking is tracked at the level
of the underlying bytestream rather than the output value.

The output from ``find()`` in verbose mode has also been
adjusted - see :ref:`the example session <verbose-output>` - to avoid
duplicating lines when the example repr is constant, even if the underlying
representation has been shrunken.

.. _v3.52.2:

-------------------
3.52.2 - 2018-03-30
-------------------

This release improves the output of failures with
:ref:`rule based stateful testing <rulebasedstateful>` in two ways:

* The output from it is now usually valid Python code.
* When the same value has two different names because it belongs to two different
  bundles, it will now display with the name associated with the correct bundle
  for a rule argument where it is used.

.. _v3.52.1:

-------------------
3.52.1 - 2018-03-29
-------------------

This release improves the behaviour of  :doc:`stateful testing <stateful>`
in two ways:

* Previously some runs would run no steps (:issue:`376`). This should no longer
  happen.
* RuleBasedStateMachine tests which used bundles extensively would often shrink
  terribly. This should now be significantly improved, though there is likely
  a lot more room for improvement.

This release also involves a low level change to how ranges of integers are
handles which may result in other improvements to shrink quality in some cases.

.. _v3.52.0:

-------------------
3.52.0 - 2018-03-24
-------------------

This release deprecates use of :func:`@settings(...) <hypothesis.settings>`
as a decorator, on functions or methods that are not also decorated with
:func:`@given <hypothesis.given>`.  You can still apply these decorators
in any order, though you should only do so once each.

Applying :func:`@given <hypothesis.given>` twice was already deprecated, and
applying :func:`@settings(...) <hypothesis.settings>` twice is deprecated in
this release and will become an error in a future version. Neither could ever
be used twice to good effect.

Using :func:`@settings(...) <hypothesis.settings>` as the sole decorator on
a test is completely pointless, so this common usage error will become an
error in a future version of Hypothesis.

.. _v3.51.0:

-------------------
3.51.0 - 2018-03-24
-------------------

This release deprecates the ``average_size`` argument to
:func:`~hypothesis.strategies.lists` and other collection strategies.
You should simply delete it wherever it was used in your tests, as it
no longer has any effect.

In early versions of Hypothesis, the ``average_size`` argument was treated
as a hint about the distribution of examples from a strategy.  Subsequent
improvements to the conceptual model and the engine for generating and
shrinking examples mean it is more effective to simply describe what
constitutes a valid example, and let our internals handle the distribution.

.. _v3.50.3:

-------------------
3.50.3 - 2018-03-24
-------------------

This patch contains some internal refactoring so that we can run
with warnings as errors in CI.

.. _v3.50.2:

-------------------
3.50.2 - 2018-03-20
-------------------

This has no user-visible changes except one slight formatting change to one docstring, to avoid a deprecation warning.

.. _v3.50.1:

-------------------
3.50.1 - 2018-03-20
-------------------

This patch fixes an internal error introduced in :ref:`3.48.0 <v3.48.0>`, where a check
for the Django test runner would expose import-time errors in Django
configuration (:issue:`1167`).

.. _v3.50.0:

-------------------
3.50.0 - 2018-03-19
-------------------

This release improves validation of numeric bounds for some strategies.

- :func:`~hypothesis.strategies.integers` and :func:`~hypothesis.strategies.floats`
  now raise ``InvalidArgument`` if passed a ``min_value`` or ``max_value``
  which is not an instance of :class:`~python:numbers.Real`, instead of
  various internal errors.
- :func:`~hypothesis.strategies.floats` now converts its bounding values to
  the nearest float above or below the min or max bound respectively, instead
  of just casting to float.  The old behaviour was incorrect in that you could
  generate ``float(min_value)``, even when this was less than ``min_value``
  itself (possible with eg. fractions).
- When both bounds are provided to :func:`~hypothesis.strategies.floats` but
  there are no floats in the interval, such as ``[(2**54)+1 .. (2**55)-1]``,
  InvalidArgument is raised.
- :func:`~hypothesis.strategies.decimals` gives a more useful error message
  if passed a string that cannot be converted to :class:`~python:decimal.Decimal`
  in a context where this error is not trapped.

Code that previously **seemed** to work may be explicitly broken if there
were no floats between ``min_value`` and ``max_value`` (only possible with
non-float bounds), or if a bound was not a :class:`~python:numbers.Real`
number but still allowed in :obj:`python:math.isnan` (some custom classes
with a ``__float__`` method).

.. _v3.49.1:

-------------------
3.49.1 - 2018-03-15
-------------------

This patch fixes our tests for Numpy dtype strategies on big-endian platforms,
where the strategy behaved correctly but the test assumed that the native byte
order was little-endian.

There is no user impact unless you are running our test suite on big-endian
platforms.  Thanks to Graham Inggs for reporting :issue:`1164`.

.. _v3.49.0:

-------------------
3.49.0 - 2018-03-12
-------------------

This release deprecates passing ``elements=None`` to collection strategies,
such as :func:`~hypothesis.strategies.lists`.

Requiring ``lists(nothing())`` or ``builds(list)`` instead of ``lists()``
means slightly more typing, but also improves the consistency and
discoverability of our API - as well as showing how to compose or
construct strategies in ways that still work in more complex situations.

Passing a nonzero max_size to a collection strategy where the elements
strategy contains no values is now deprecated, and will be an error in a
future version.  The equivalent with ``elements=None`` is already an error.

.. _v3.48.1:

-------------------
3.48.1 - 2018-03-05
-------------------

This patch will minimize examples that would come out non-minimal in previous versions. Thanks to Kyle Reeve for this patch.

.. _v3.48.0:

-------------------
3.48.0 - 2018-03-05
-------------------

This release improves some "unhappy paths" when using Hypothesis
with the standard library :mod:`python:unittest` module:

- Applying :func:`@given <hypothesis.given>` to a non-test method which is
  overridden from :class:`python:unittest.TestCase`, such as ``setUp``,
  raises :attr:`a new health check <hypothesis.HealthCheck.not_a_test_method>`.
  (:issue:`991`)
- Using :meth:`~python:unittest.TestCase.subTest` within a test decorated
  with :func:`@given <hypothesis.given>` would leak intermediate results
  when tests were run under the :mod:`python:unittest` test runner.
  Individual reporting of failing subtests is now disabled during a test
  using :func:`@given <hypothesis.given>`.  (:issue:`1071`)
- :func:`@given <hypothesis.given>` is still not a class decorator, but the
  error message if you try using it on a class has been improved.

As a related improvement, using :class:`django:django.test.TestCase` with
:func:`@given <hypothesis.given>` instead of
:class:`hypothesis.extra.django.TestCase` raises an explicit error instead
of running all examples in a single database transaction.

.. _v3.47.0:

-------------------
3.47.0 - 2018-03-02
-------------------

:obj:`~hypothesis.settings.register_profile` now accepts keyword arguments
for specific settings, and the parent settings object is now optional.
Using a ``name`` for a registered profile which is not a string was never
suggested, but it is now also deprecated and will eventually be an error.

.. _v3.46.2:

-------------------
3.46.2 - 2018-03-01
-------------------

This release removes an unnecessary branch from the code, and has no user-visible impact.

.. _v3.46.1:

-------------------
3.46.1 - 2018-03-01
-------------------

This changes only the formatting of our docstrings and should have no user-visible effects.

.. _v3.46.0:

-------------------
3.46.0 - 2018-02-26
-------------------

:func:`~hypothesis.strategies.characters` has improved docs about
what arguments are valid, and additional validation logic to raise a
clear error early (instead of e.g. silently ignoring a bad argument).
Categories may be specified as the Unicode 'general category'
(eg ``u'Nd'``), or as the 'major category' (eg ``[u'N', u'Lu']``
is equivalent to ``[u'Nd', u'Nl', u'No', u'Lu']``).

In previous versions, general categories were supported and all other
input was silently ignored.  Now, major categories are supported in
addition to general categories (which may change the behaviour of some
existing code), and all other input is deprecated.

.. _v3.45.5:

-------------------
3.45.5 - 2018-02-26
-------------------

This patch improves strategy inference in ``hypothesis.extra.django``
to account for some validators in addition to field type - see
:issue:`1116` for ongoing work in this space.

Specifically, if a :class:`~django:django.db.models.CharField` or
:class:`~django:django.db.models.TextField` has an attached
:class:`~django:django.core.validators.RegexValidator`, we now use
:func:`~hypothesis.strategies.from_regex` instead of
:func:`~hypothesis.strategies.text` as the underlying strategy.
This allows us to generate examples of the default
:class:`~django:django.contrib.auth.models.User` model, closing :issue:`1112`.

.. _v3.45.4:

-------------------
3.45.4 - 2018-02-25
-------------------

This patch improves some internal debugging information, fixes
a typo in a validation error message, and expands the documentation
for new contributors.

.. _v3.45.3:

-------------------
3.45.3 - 2018-02-23
-------------------

This patch may improve example shrinking slightly for some strategies.

.. _v3.45.2:

-------------------
3.45.2 - 2018-02-18
-------------------

This release makes our docstring style more consistent, thanks to
:pypi:`flake8-docstrings`.  There are no user-visible changes.

.. _v3.45.1:

-------------------
3.45.1 - 2018-02-17
-------------------

This fixes an indentation issue in docstrings for
:func:`~hypothesis.strategies.datetimes`, :func:`~hypothesis.strategies.dates`,
:func:`~hypothesis.strategies.times`, and
:func:`~hypothesis.strategies.timedeltas`.

.. _v3.45.0:

-------------------
3.45.0 - 2018-02-13
-------------------

This release fixes :func:`~hypothesis.strategies.builds` so that ``target``
can be used as a keyword argument for passing values to the target. The target
itself can still be specified as a keyword argument, but that behavior is now
deprecated. The target should be provided as the first positional argument.

.. _v3.44.26:

--------------------
3.44.26 - 2018-02-06
--------------------

This release fixes some formatting issues in the Hypothesis source code.
It should have no externally visible effects.

.. _v3.44.25:

--------------------
3.44.25 - 2018-02-05
--------------------

This release changes the way in which Hypothesis tries to shrink the size of
examples. It probably won't have much impact, but might make shrinking faster
in some cases. It is unlikely but not impossible that it will change the
resulting examples.

.. _v3.44.24:

--------------------
3.44.24 - 2018-01-27
--------------------

This release fixes dependency information when installing Hypothesis
from a binary "wheel" distribution.

- The ``install_requires`` for :pypi:`enum34` is resolved at install
  time, rather than at build time (with potentially different results).
- Django has fixed their ``python_requires`` for versions 2.0.0 onward,
  simplifying Python2-compatible constraints for downstream projects.

.. _v3.44.23:

--------------------
3.44.23 - 2018-01-24
--------------------

This release improves shrinking in a class of pathological examples that you
are probably never hitting in practice. If you *are* hitting them in practice
this should be a significant speed up in shrinking. If you are not, you are
very unlikely to notice any difference. You might see a slight slow down and/or
slightly better falsifying examples.

.. _v3.44.22:

--------------------
3.44.22 - 2018-01-23
--------------------

This release fixes a dependency problem.  It was possible to install
Hypothesis with an old version of :pypi:`attrs`, which would throw a
``TypeError`` as soon as you tried to import hypothesis.  Specifically, you
need attrs 16.0.0 or newer.

Hypothesis will now require the correct version of attrs when installing.

.. _v3.44.21:

--------------------
3.44.21 - 2018-01-22
--------------------

This change adds some additional structural information that Hypothesis will
use to guide its search.

You mostly shouldn't see much difference from this. The two most likely effects
you would notice are:

1. Hypothesis stores slightly more examples in its database for passing tests.
2. Hypothesis *may* find new bugs that it was previously missing, but it
   probably won't (this is a basic implementation of the feature that is
   intended to support future work. Although it is useful on its own, it's not
   *very* useful on its own).

.. _v3.44.20:

--------------------
3.44.20 - 2018-01-21
--------------------

This is a small refactoring release that changes how Hypothesis tracks some
information about the boundary of examples in its internal representation.

You are unlikely to see much difference in behaviour, but memory usage and
run time may both go down slightly during normal test execution, and when
failing Hypothesis might print its failing example slightly sooner.

.. _v3.44.19:

--------------------
3.44.19 - 2018-01-21
--------------------

This changes how we compute the default ``average_size`` for all collection
strategies. Previously setting a ``max_size`` without setting an
``average_size`` would have the seemingly paradoxical effect of making data
generation *slower*, because it would raise the average size from its default.
Now setting ``max_size`` will either leave the default unchanged or lower it
from its default.

If you are currently experiencing this problem, this may make your tests
substantially faster. If you are not, this will likely have no effect on you.

.. _v3.44.18:

--------------------
3.44.18 - 2018-01-20
--------------------

This is a small refactoring release that changes how Hypothesis detects when
the structure of data generation depends on earlier values generated (e.g. when
using :ref:`flatmap <flatmap>` or :func:`~hypothesis.strategies.composite`).
It should not have any observable effect on behaviour.

.. _v3.44.17:

--------------------
3.44.17 - 2018-01-15
--------------------

This release fixes a typo in internal documentation, and has no user-visible impact.

.. _v3.44.16:

--------------------
3.44.16 - 2018-01-13
--------------------

This release improves test case reduction for recursive data structures.
Hypothesis now guarantees that whenever a strategy calls itself recursively
(usually this will happen because you are using :func:`~hypothesis.strategies.deferred`),
any recursive call may replace the top level value. e.g. given a tree structure,
Hypothesis will always try replacing it with a subtree.

Additionally this introduces a new heuristic that may in some circumstances
significantly speed up test case reduction - Hypothesis should be better at
immediately replacing elements drawn inside another strategy with their minimal
possible value.

.. _v3.44.15:

--------------------
3.44.15 - 2018-01-13
--------------------

:func:`~hypothesis.strategies.from_type` can now resolve recursive types
such as binary trees (:issue:`1004`).  Detection of non-type arguments has
also improved, leading to better error messages in many cases involving
:pep:`forward references <484#forward-references>`.

.. _v3.44.14:

--------------------
3.44.14 - 2018-01-08
--------------------

This release fixes a bug in the shrinker that prevented the optimisations in
:ref:`3.44.6 <v3.44.6>` from working in some cases. It would not have worked correctly when
filtered examples were nested (e.g. with a set of integers in some range).

This would not have resulted in any correctness problems, but shrinking may
have been slower than it otherwise could be.

.. _v3.44.13:

--------------------
3.44.13 - 2018-01-08
--------------------

This release changes the average bit length of values drawn from
:func:`~hypothesis.strategies.integers` to be much smaller. Additionally it
changes the shrinking order so that now size is considered before sign - e.g.
-1 will be preferred to +10.

The new internal format for integers required some changes to the minimizer to
make work well, so you may also see some improvements to example quality in
unrelated areas.

.. _v3.44.12:

--------------------
3.44.12 - 2018-01-07
--------------------

This changes Hypothesis's internal implementation of weighted sampling. This
will affect example distribution and quality, but you shouldn't see any other
effects.

.. _v3.44.11:

--------------------
3.44.11 - 2018-01-06
--------------------

This is a change to some internals around how Hypothesis handles avoiding
generating duplicate examples and seeking out novel regions of the search
space.

You are unlikely to see much difference as a result of it, but it fixes
a bug where an internal assertion could theoretically be triggered and has some
minor effects on the distribution of examples so could potentially find bugs
that have previously been missed.

.. _v3.44.10:

--------------------
3.44.10 - 2018-01-06
--------------------

This patch avoids creating debug statements when debugging is disabled.
Profiling suggests this is a 5-10% performance improvement (:pull:`1040`).

.. _v3.44.9:

-------------------
3.44.9 - 2018-01-06
-------------------

This patch blacklists null characters (``'\x00'``) in automatically created
strategies for Django :obj:`~django:django.db.models.CharField` and
:obj:`~django:django.db.models.TextField`, due to a database issue which
`was recently fixed upstream <https://code.djangoproject.com/ticket/28201>`_
(Hypothesis :issue:`1045`).

.. _v3.44.8:

-------------------
3.44.8 - 2018-01-06
-------------------

This release makes the Hypothesis shrinker slightly less greedy in order to
avoid local minima - when it gets stuck, it makes a small attempt to search
around the final example it would previously have returned to find a new
starting point to shrink from. This should improve example quality in some
cases, especially ones where the test data has dependencies among parts of it
that make it difficult for Hypothesis to proceed.

.. _v3.44.7:

-------------------
3.44.7 - 2018-01-04
-------------------

This release adds support for `Django 2
<https://www.djangoproject.com/weblog/2017/dec/02/django-20-released/>`_ in
the hypothesis-django extra.

This release drops support for Django 1.10, as it is no longer supported by
the Django team.

.. _v3.44.6:

-------------------
3.44.6 - 2018-01-02
-------------------

This release speeds up test case reduction in many examples by being better at
detecting large shrinks it can use to discard redundant parts of its input.
This will be particularly noticeable in examples that make use of filtering
and for some integer ranges.

.. _v3.44.5:

-------------------
3.44.5 - 2018-01-02
-------------------

Happy new year!

This is a no-op release that updates the year range on all of
the copyright headers in our source to include 2018.

.. _v3.44.4:

-------------------
3.44.4 - 2017-12-23
-------------------

This release fixes :issue:`1044`, which slowed tests by up to 6%
due to broken caching.

.. _v3.44.3:

-------------------
3.44.3 - 2017-12-21
-------------------

This release improves the shrinker in cases where examples drawn earlier can
affect how much data is drawn later (e.g. when you draw a length parameter in
a composite and then draw that many elements). Examples found in cases like
this should now be much closer to minimal.

.. _v3.44.2:

-------------------
3.44.2 - 2017-12-20
-------------------

This is a pure refactoring release which changes how Hypothesis manages its
set of examples internally. It should have no externally visible effects.

.. _v3.44.1:

-------------------
3.44.1 - 2017-12-18
-------------------

This release fixes :issue:`997`, in which under some circumstances the body of
tests run under Hypothesis would not show up when run under coverage even
though the tests were run and the code they called outside of the test file
would show up normally.

.. _v3.44.0:

-------------------
3.44.0 - 2017-12-17
-------------------

This release adds a new feature: The :func:`@reproduce_failure <hypothesis.reproduce_failure>` decorator,
designed to make it easy to use Hypothesis's binary format for examples to
reproduce a problem locally without having to share your example database
between machines.

This also changes when seeds are printed:

* They will no longer be printed for
  normal falsifying examples, as there are now adequate ways of reproducing those
  for all cases, so it just contributes noise.
* They will once again be printed when reusing examples from the database, as
  health check failures should now be more reliable in this scenario so it will
  almost always work in this case.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.43.1:

-------------------
3.43.1 - 2017-12-17
-------------------

This release fixes a bug with Hypothesis's database management - examples that
were found in the course of shrinking were saved in a way that indicated that
they had distinct causes, and so they would all be retried on the start of the
next test. The intended behaviour, which is now what is implemented, is that
only a bounded subset of these examples would be retried.

.. _v3.43.0:

-------------------
3.43.0 - 2017-12-17
-------------------

:exc:`~hypothesis.errors.HypothesisDeprecationWarning` now inherits from
:exc:`python:FutureWarning` instead of :exc:`python:DeprecationWarning`,
as recommended by :pep:`565` for user-facing warnings (:issue:`618`).
If you have not changed the default warnings settings, you will now see
each distinct :exc:`~hypothesis.errors.HypothesisDeprecationWarning`
instead of only the first.

.. _v3.42.2:

-------------------
3.42.2 - 2017-12-12
-------------------

This patch fixes :issue:`1017`, where instances of a list or tuple subtype
used as an argument to a strategy would be coerced to tuple.

.. _v3.42.1:

-------------------
3.42.1 - 2017-12-10
-------------------

This release has some internal cleanup, which makes reading the code
more pleasant and may shrink large examples slightly faster.

.. _v3.42.0:

-------------------
3.42.0 - 2017-12-09
-------------------

This release deprecates ``faker-extra``, which was designed as a transition
strategy but does not support example shrinking or coverage-guided discovery.

.. _v3.41.0:

-------------------
3.41.0 - 2017-12-06
-------------------

:func:`~hypothesis.strategies.sampled_from` can now sample from
one-dimensional numpy ndarrays. Sampling from multi-dimensional
ndarrays still results in a deprecation warning. Thanks to Charlie
Tanksley for this patch.

.. _v3.40.1:

-------------------
3.40.1 - 2017-12-04
-------------------

This release makes two changes:

* It makes the calculation of some of the metadata that Hypothesis uses for
  shrinking occur lazily. This should speed up performance of test case
  generation a bit because it no longer calculates information it doesn't need.
* It improves the shrinker for certain classes of nested examples. e.g. when
  shrinking lists of lists, the shrinker is now able to concatenate two
  adjacent lists together into a single list. As a result of this change,
  shrinking may get somewhat slower when the minimal example found is large.

.. _v3.40.0:

-------------------
3.40.0 - 2017-12-02
-------------------

This release improves how various ways of seeding Hypothesis interact with the
example database:

* Using the example database with :func:`~hypothesis.seed` is now deprecated.
  You should set ``database=None`` if you are doing that. This will only warn
  if you actually load examples from the database while using ``@seed``.
* The :attr:`~hypothesis.settings.derandomize` will behave the same way as
  ``@seed``.
* Using ``--hypothesis-seed`` will disable use of the database.
* If a test used examples from the database, it will not suggest using a seed
  to reproduce it, because that won't work.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.39.0:

-------------------
3.39.0 - 2017-12-01
-------------------

This release adds a new health check that checks if the smallest "natural"
possible example of your test case is very large - this will tend to cause
Hypothesis to generate bad examples and be quite slow.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.38.9:

-------------------
3.38.9 - 2017-11-29
-------------------

This is a documentation release to improve the documentation of shrinking
behaviour for Hypothesis's strategies.

.. _v3.38.8:

-------------------
3.38.8 - 2017-11-29
-------------------

This release improves the performance of
:func:`~hypothesis.strategies.characters` when using ``blacklist_characters``
and :func:`~hypothesis.strategies.from_regex` when using negative character
classes.

The problems this fixes were found in the course of work funded by
`Smarkets <https://smarkets.com/>`_.

.. _v3.38.7:

-------------------
3.38.7 - 2017-11-29
-------------------

This is a patch release for :func:`~hypothesis.strategies.from_regex`, which
had a bug in handling of the :obj:`python:re.VERBOSE` flag (:issue:`992`).
Flags are now handled correctly when parsing regex.

.. _v3.38.6:

-------------------
3.38.6 - 2017-11-28
-------------------

This patch changes a few byte-string literals from double to single quotes,
thanks to an update in :pypi:`unify`.  There are no user-visible changes.

.. _v3.38.5:

-------------------
3.38.5 - 2017-11-23
-------------------

This fixes the repr of strategies using lambda that are defined inside
decorators to include the lambda source.

This would mostly have been visible when using the
:ref:`statistics <statistics>` functionality - lambdas used for e.g. filtering
would have shown up with a ``<unknown>`` as their body. This can still happen,
but it should happen less often now.

.. _v3.38.4:

-------------------
3.38.4 - 2017-11-22
-------------------

This release updates the reported :ref:`statistics <statistics>` so that they
show approximately what fraction of your test run time is spent in data
generation (as opposed to test execution).

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.38.3:

-------------------
3.38.3 - 2017-11-21
-------------------

This is a documentation release, which ensures code examples are up to date
by running them as doctests in CI (:issue:`711`).

.. _v3.38.2:

-------------------
3.38.2 - 2017-11-21
-------------------

This release changes the behaviour of the :attr:`~hypothesis.settings.deadline`
setting when used with :func:`~hypothesis.strategies.data`: Time spent inside
calls to ``data.draw`` will no longer be counted towards the deadline time.

As a side effect of some refactoring required for this work, the way flaky
tests are handled has changed slightly. You are unlikely to see much difference
from this, but some error messages will have changed.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.38.1:

-------------------
3.38.1 - 2017-11-21
-------------------

This patch has a variety of non-user-visible refactorings, removing various
minor warts ranging from indirect imports to typos in comments.

.. _v3.38.0:

-------------------
3.38.0 - 2017-11-18
-------------------

This release overhauls :doc:`the health check system <healthchecks>`
in a variety of small ways.
It adds no new features, but is nevertheless a minor release because it changes
which tests are likely to fail health checks.

The most noticeable effect is that some tests that used to fail health checks
will now pass, and some that used to pass will fail. These should all be
improvements in accuracy. In particular:

* New failures will usually be because they are now taking into account things
  like use of :func:`~hypothesis.strategies.data` and
  :func:`~hypothesis.assume` inside the test body.
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

.. _v3.37.0:

-------------------
3.37.0 - 2017-11-12
-------------------

This is a deprecation release for some health check related features.

The following are now deprecated:

* Passing ``HealthCheck.exception_in_generation`` to
  :attr:`~hypothesis.settings.suppress_health_check`. This no longer does
  anything even when passed -  All errors that occur during data generation
  will now be immediately reraised rather than going through the health check
  mechanism.
* Passing ``HealthCheck.random_module`` to
  :attr:`~hypothesis.settings.suppress_health_check`. This hasn't done anything
  for a long time, but was never explicitly deprecated. Hypothesis always seeds
  the random module when running :func:`@given <hypothesis.given>` tests, so this
  is no longer an error and suppressing it doesn't do anything.
* Passing non-:class:`~hypothesis.HealthCheck` values in
  :attr:`~hypothesis.settings.suppress_health_check`. This was previously
  allowed but never did anything useful.

In addition, passing a non-iterable value as :attr:`~hypothesis.settings.suppress_health_check`
will now raise an error immediately (it would never have worked correctly, but
it would previously have failed later). Some validation error messages have
also been updated.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.36.1:

-------------------
3.36.1 - 2017-11-10
-------------------

This is a yak shaving release, mostly concerned with our own tests.

While :func:`~python:inspect.getfullargspec` was documented as deprecated
in Python 3.5, it never actually emitted a warning.  Our code to silence
this (nonexistent) warning has therefore been removed.

We now run our tests with ``DeprecationWarning`` as an error, and made some
minor changes to our own tests as a result.  This required similar upstream
updates to :pypi:`coverage` and :pypi:`execnet` (a test-time dependency via
:pypi:`pytest-xdist`).

There is no user-visible change in Hypothesis itself, but we encourage you
to consider enabling deprecations as errors in your own tests.

.. _v3.36.0:

-------------------
3.36.0 - 2017-11-06
-------------------

This release adds a setting to the public API, and does some internal cleanup:

- The :attr:`~hypothesis.settings.derandomize` setting is now documented (:issue:`890`)
- Removed - and disallowed - all 'bare excepts' in Hypothesis (:issue:`953`)
- Documented the ``strict`` setting as deprecated, and
  updated the build so our docs always match deprecations in the code.

.. _v3.35.0:

-------------------
3.35.0 - 2017-11-06
-------------------

This minor release supports constraining :func:`~hypothesis.strategies.uuids`
to generate a particular version of :class:`~python:uuid.UUID` (:issue:`721`).

Thanks to Dion Misic for this feature.

.. _v3.34.1:

-------------------
3.34.1 - 2017-11-02
-------------------

This patch updates the documentation to suggest
:func:`builds(callable) <hypothesis.strategies.builds>` instead of
:func:`just(callable()) <hypothesis.strategies.just>`.

.. _v3.34.0:

-------------------
3.34.0 - 2017-11-02
-------------------

Hypothesis now emits deprecation warnings if you apply
:func:`@given <hypothesis.given>` more than once to a target.

Applying :func:`@given <hypothesis.given>` repeatedly wraps the target multiple
times. Each wrapper will search the space of of possible parameters separately.
This is equivalent but will be much more inefficient than doing it with a
single call to :func:`@given <hypothesis.given>`.

For example, instead of
``@given(booleans()) @given(integers())``, you could write
``@given(booleans(), integers())``

.. _v3.33.1:

-------------------
3.33.1 - 2017-11-02
-------------------

This is a bugfix release:

- :func:`~hypothesis.strategies.builds` would try to infer a strategy for
  required positional arguments of the target from type hints, even if they
  had been given to :func:`~hypothesis.strategies.builds` as positional
  arguments (:issue:`946`).  Now it only infers missing required arguments.
- An internal introspection function wrongly reported ``self`` as a required
  argument for bound methods, which might also have affected
  :func:`~hypothesis.strategies.builds`.  Now it knows better.

.. _v3.33.0:

-------------------
3.33.0 - 2017-10-16
-------------------

This release supports strategy inference for more Django field types - you can now omit an argument for
Date, Time, Duration, Slug, IP Address, and UUID fields.  (:issue:`642`)

Strategy generation for fields with grouped choices now selects choices from
each group, instead of selecting from the group names.

.. _v3.32.2:

-------------------
3.32.2 - 2017-10-15
-------------------

This patch removes the ``mergedb`` tool, introduced in Hypothesis 1.7.1
on an experimental basis.  It has never actually worked, and the new
:doc:`Hypothesis example database <database>` is designed to make such a
tool unnecessary.

.. _v3.32.1:

-------------------
3.32.1 - 2017-10-13
-------------------

This patch has two improvements for strategies based on enumerations.

- :func:`~hypothesis.strategies.from_type` now handles enumerations correctly,
  delegating to :func:`~hypothesis.strategies.sampled_from`.  Previously it
  noted that ``Enum.__init__`` has no required arguments and therefore delegated
  to :func:`~hypothesis.strategies.builds`, which would subsequently fail.
- When sampling from an :class:`python:enum.Flag`, we also generate combinations
  of members. Eg for ``Flag('Permissions', 'READ, WRITE, EXECUTE')`` we can now
  generate, ``Permissions.READ``, ``Permissions.READ|WRITE``, and so on.

.. _v3.32.0:

-------------------
3.32.0 - 2017-10-09
-------------------

This changes the default value of
the ``use_coverage`` setting to True when
running on pypy (it was already True on CPython).

It was previously set to False because we expected it to be too slow, but
recent benchmarking shows that actually performance of the feature on pypy is
fairly acceptable - sometimes it's slower than on CPython, sometimes it's
faster, but it's generally within a factor of two either way.

.. _v3.31.6:

-------------------
3.31.6 - 2017-10-08
-------------------

This patch improves the quality of strategies inferred from Numpy dtypes:

* Integer dtypes generated examples with the upper half of their (non-sign) bits
  set to zero.  The inferred strategies can now produce any representable integer.
* Fixed-width unicode- and byte-string dtypes now cap the internal example
  length, which should improve example and shrink quality.
* Numpy arrays can only store fixed-size strings internally, and allow shorter
  strings by right-padding them with null bytes.  Inferred string strategies
  no longer generate such values, as they can never be retrieved from an array.
  This improves shrinking performance by skipping useless values.

This has already been useful in Hypothesis - we found an overflow bug in our
Pandas support, and as a result :func:`~hypothesis.extra.pandas.indexes` and
:func:`~hypothesis.extra.pandas.range_indexes` now check that ``min_size``
and ``max_size`` are at least zero.

.. _v3.31.5:

-------------------
3.31.5 - 2017-10-08
-------------------

This release fixes a performance problem in tests where
the ``use_coverage`` setting is True.

Tests experience a slow-down proportionate to the amount of code they cover.
This is still the case, but the factor is now low enough that it should be
unnoticeable. Previously it was large and became much larger in :ref:`3.30.4 <v3.30.4>`.

.. _v3.31.4:

-------------------
3.31.4 - 2017-10-08
-------------------

:func:`~hypothesis.strategies.from_type` failed with a very confusing error
if passed a :func:`~python:typing.NewType` (:issue:`901`).  These psudeo-types
are now unwrapped correctly, and strategy inference works as expected.

.. _v3.31.3:

-------------------
3.31.3 - 2017-10-06
-------------------

This release makes some small optimisations to our use of coverage that should
reduce constant per-example overhead. This is probably only noticeable on
examples where the test itself is quite fast. On no-op tests that don't test
anything you may see up to a fourfold speed increase (which is still
significantly slower than without coverage). On more realistic tests the speed
up is likely to be less than that.

.. _v3.31.2:

-------------------
3.31.2 - 2017-09-30
-------------------

This release fixes some formatting and small typos/grammar issues in the
documentation, specifically the page docs/settings.rst, and the inline docs
for the various settings.

.. _v3.31.1:

-------------------
3.31.1 - 2017-09-30
-------------------

This release improves the handling of deadlines so that they act better with
the shrinking process. This fixes :issue:`892`.

This involves two changes:

1. The deadline is raised during the initial generation and shrinking, and then
   lowered to the set value for final replay. This restricts our attention to
   examples which exceed the deadline by a more significant margin, which
   increases their reliability.
2. When despite the above a test still becomes flaky because it is
   significantly faster on rerun than it was on its first run, the error
   message is now more explicit about the nature of this problem, and includes
   both the initial test run time and the new test run time.

In addition, this release also clarifies the documentation of the deadline
setting slightly to be more explicit about where it applies.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.31.0:

-------------------
3.31.0 - 2017-09-29
-------------------

This release blocks installation of Hypothesis on Python 3.3, which
:PEP:`reached its end of life date on 2017-09-29 <398>`.

This should not be of interest to anyone but downstream maintainers -
if you are affected, migrate to a secure version of Python as soon as
possible or at least seek commercial support.

.. _v3.30.4:

-------------------
3.30.4 - 2017-09-27
-------------------

This release makes several changes:

1. It significantly improves Hypothesis's ability to use coverage information
   to find interesting examples.
2. It reduces the default :attr:`~hypothesis.settings.max_examples` setting from 200 to 100. This takes
   advantage of the improved algorithm meaning fewer examples are typically
   needed to get the same testing and is sufficiently better at covering
   interesting behaviour, and offsets some of the performance problems of
   running under coverage.
3. Hypothesis will always try to start its testing with an example that is near
   minimized.

The new algorithm for 1 also makes some changes to Hypothesis's low level data
generation which apply even with coverage turned off. They generally reduce the
total amount of data generated, which should improve test performance somewhat.
Between this and 3 you should see a noticeable reduction in test runtime (how
much so depends on your tests and how much example size affects their
performance. On our benchmarks, where data generation dominates, we saw up to
a factor of two performance improvement, but it's unlikely to be that large.

.. _v3.30.3:

-------------------
3.30.3 - 2017-09-25
-------------------

This release fixes some formatting and small typos/grammar issues in the
documentation, specifically the page docs/details.rst, and some inline
docs linked from there.

.. _v3.30.2:

-------------------
3.30.2 - 2017-09-24
-------------------

This release changes Hypothesis's caching approach for functions in
``hypothesis.strategies``. Previously it would have cached extremely
aggressively and cache entries would never be evicted. Now it adopts a
least-frequently used, least recently used key invalidation policy, and is
somewhat more conservative about which strategies it caches.

Workloads which create strategies based on dynamic values, e.g. by using
:ref:`flatmap <flatmap>` or :func:`~hypothesis.strategies.composite`,
will use significantly less memory.

.. _v3.30.1:

-------------------
3.30.1 - 2017-09-22
-------------------

This release fixes a bug where when running with
the ``use_coverage=True`` setting inside an
existing running instance of coverage, Hypothesis would frequently put files
that the coveragerc excluded in the report for the enclosing coverage.

.. _v3.30.0:

-------------------
3.30.0 - 2017-09-20
-------------------

This release introduces two new features:

* When a test fails, either with a health check failure or a falsifying example,
  Hypothesis will print out a seed that led to that failure, if the test is not
  already running with a fixed seed. You can then recreate that failure using either
  the :func:`@seed <hypothesis.seed>` decorator or (if you are running pytest) with ``--hypothesis-seed``.
* :pypi:`pytest` users can specify a seed to use for :func:`@given <hypothesis.given>` based tests by passing
  the ``--hypothesis-seed`` command line argument.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.29.0:

-------------------
3.29.0 - 2017-09-19
-------------------

This release makes Hypothesis coverage aware. Hypothesis now runs all test
bodies under coverage, and uses this information to guide its testing.

The ``use_coverage`` setting can be used to disable
this behaviour if you want to test code that is sensitive to coverage being
enabled (either because of performance or interaction with the trace function).

The main benefits of this feature are:

* Hypothesis now observes when examples it discovers cover particular lines
  or branches and stores them in the database for later.
* Hypothesis will make some use of this information to guide its exploration of
  the search space and improve the examples it finds (this is currently used
  only very lightly and will likely improve significantly in future releases).

This also has the following side-effects:

* Hypothesis now has an install time dependency on the :pypi:`coverage` package.
* Tests that are already running Hypothesis under coverage will likely get
  faster.
* Tests that are not running under coverage now run their test bodies under
  coverage by default.


This feature is only partially supported under pypy. It is significantly slower
than on CPython and is turned off by default as a result, but it should still
work correctly if you want to use it.

.. _v3.28.3:

-------------------
3.28.3 - 2017-09-18
-------------------

This release is an internal change that affects how Hypothesis handles
calculating certain properties of strategies.

The primary effect of this is that it fixes a bug where use of
:func:`~hypothesis.strategies.deferred` could sometimes trigger an internal assertion
error. However the fix for this bug involved some moderately deep changes to
how Hypothesis handles certain constructs so you may notice some additional
knock-on effects.

In particular the way Hypothesis handles drawing data from strategies that
cannot generate any values has changed to bail out sooner than it previously
did. This may speed up certain tests, but it is unlikely to make much of a
difference in practice for tests that were not already failing with
Unsatisfiable.

.. _v3.28.2:

-------------------
3.28.2 - 2017-09-18
-------------------

This is a patch release that fixes a bug in the :mod:`hypothesis.extra.pandas`
documentation where it incorrectly referred to :func:`~hypothesis.extra.pandas.column`
instead of :func:`~hypothesis.extra.pandas.columns`.

.. _v3.28.1:

-------------------
3.28.1 - 2017-09-16
-------------------

This is a refactoring release. It moves a number of internal uses
of :func:`~python:collections.namedtuple` over to using attrs based classes, and removes a couple
of internal namedtuple classes that were no longer in use.

It should have no user visible impact.

.. _v3.28.0:

-------------------
3.28.0 - 2017-09-15
-------------------

This release adds support for testing :pypi:`pandas` via the :ref:`hypothesis.extra.pandas <hypothesis-pandas>`
module.

It also adds a dependency on :pypi:`attrs`.

This work was funded by `Stripe <https://stripe.com/>`_.

.. _v3.27.1:

-------------------
3.27.1 - 2017-09-14
-------------------

This release fixes some formatting and broken cross-references in the
documentation, which includes editing docstrings - and thus a patch release.

.. _v3.27.0:

-------------------
3.27.0 - 2017-09-13
-------------------

This release introduces a :attr:`~hypothesis.settings.deadline`
setting to Hypothesis.

When set this turns slow tests into errors. By default it is unset but will
warn if you exceed 200ms, which will become the default value in a future
release.

This work was funded by `Smarkets <https://smarkets.com/>`_.

.. _v3.26.0:

-------------------
3.26.0 - 2017-09-12
-------------------

Hypothesis now emits deprecation warnings if you are using the legacy
SQLite example database format, or the tool for merging them. These were
already documented as deprecated, so this doesn't change their deprecation
status, only that we warn about it.

.. _v3.25.1:

-------------------
3.25.1 - 2017-09-12
-------------------

This release fixes a bug with generating :doc:`numpy datetime and timedelta types <numpy:reference/arrays.datetime>`:
When inferring the strategy from the dtype, datetime and timedelta dtypes with
sub-second precision would always produce examples with one second resolution.
Inferring a strategy from a time dtype will now always produce example with the
same precision.

.. _v3.25.0:

-------------------
3.25.0 - 2017-09-12
-------------------

This release changes how Hypothesis shrinks and replays examples to take into
account that it can encounter new bugs while shrinking the bug it originally
found. Previously it would end up replacing the originally found bug with the
new bug and show you only that one. Now it is (often) able to recognise when
two bugs are distinct and when it finds more than one will show both.

.. _v3.24.2:

-------------------
3.24.2 - 2017-09-11
-------------------

This release removes the (purely internal and no longer useful)
``strategy_test_suite`` function and the corresponding strategytests module.

.. _v3.24.1:

-------------------
3.24.1 - 2017-09-06
-------------------

This release improves the reduction of examples involving floating point
numbers to produce more human readable examples.

It also has some general purpose changes to the way the minimizer works
internally, which may see some improvement in quality and slow down of test
case reduction in cases that have nothing to do with floating point numbers.

.. _v3.24.0:

-------------------
3.24.0 - 2017-09-05
-------------------

Hypothesis now emits deprecation warnings if you use ``some_strategy.example()`` inside a
test function or strategy definition (this was never intended to be supported,
but is sufficiently widespread that it warrants a deprecation path).

.. _v3.23.3:

-------------------
3.23.3 - 2017-09-05
-------------------

This is a bugfix release for :func:`~hypothesis.strategies.decimals`
with the ``places`` argument.

- No longer fails health checks (:issue:`725`, due to internal filtering)
- Specifying a ``min_value`` and ``max_value`` without any decimals with
  ``places`` places between them gives a more useful error message.
- Works for any valid arguments, regardless of the decimal precision context.

.. _v3.23.2:

-------------------
3.23.2 - 2017-09-01
-------------------

This is a small refactoring release that removes a now-unused parameter to an
internal API. It shouldn't have any user visible effect.

.. _v3.23.1:

-------------------
3.23.1 - 2017-09-01
-------------------

Hypothesis no longer propagates the dynamic scope of settings into strategy
definitions.

This release is a small change to something that was never part of the public
API and you will almost certainly not notice any effect unless you're doing
something surprising, but for example the following code will now give a
different answer in some circumstances:

.. code-block:: python

    import hypothesis.strategies as st
    from hypothesis import settings

    CURRENT_SETTINGS = st.builds(lambda: settings.default)

(We don't actually encourage you writing code like this)

Previously this would have generated the settings that were in effect at the
point of definition of ``CURRENT_SETTINGS``. Now it will generate the settings
that are used for the current test.

It is very unlikely to be significant enough to be visible, but you may also
notice a small performance improvement.

.. _v3.23.0:

-------------------
3.23.0 - 2017-08-31
-------------------

This release adds a ``unique`` argument to :func:`~hypothesis.extra.numpy.arrays`
which behaves the same ways as the corresponding one for
:func:`~hypothesis.strategies.lists`, requiring all of the elements in the
generated array to be distinct.

.. _v3.22.2:

-------------------
3.22.2 - 2017-08-29
-------------------

This release fixes an issue where Hypothesis would raise a ``TypeError`` when
using the datetime-related strategies if running with ``PYTHONOPTIMIZE=2``.
This bug was introduced in :ref:`3.20.0 <v3.20.0>`.  (See :issue:`822`)

.. _v3.22.1:

-------------------
3.22.1 - 2017-08-28
-------------------

Hypothesis now transparently handles problems with an internal unicode cache,
including file truncation or read-only filesystems (:issue:`767`).
Thanks to Sam Hames for the patch.

.. _v3.22.0:

-------------------
3.22.0 - 2017-08-26
-------------------

This release provides what should be a substantial performance improvement to
numpy arrays generated using :ref:`provided numpy support <hypothesis-numpy>`,
and adds a new ``fill_value`` argument to :func:`~hypothesis.extra.numpy.arrays`
to control this behaviour.

This work was funded by `Stripe <https://stripe.com/>`_.

.. _v3.21.3:

-------------------
3.21.3 - 2017-08-26
-------------------

This release fixes some extremely specific circumstances that probably have
never occurred in the wild where users of
:func:`~hypothesis.strategies.deferred` might have seen a :class:`python:RuntimeError` from
too much recursion, usually in cases where no valid example could have been
generated anyway.

.. _v3.21.2:

-------------------
3.21.2 - 2017-08-25
-------------------

This release fixes some minor bugs in argument validation:

    * :ref:`hypothesis.extra.numpy <hypothesis-numpy>` dtype strategies would raise an internal error
      instead of an InvalidArgument exception when passed an invalid
      endianness specification.
    * :func:`~hypothesis.strategies.fractions` would raise an internal error instead of an InvalidArgument
      if passed ``float("nan")`` as one of its bounds.
    * The error message for passing ``float("nan")`` as a bound to various
      strategies has been improved.
    * Various bound arguments will now raise InvalidArgument in cases where
      they would previously have raised an internal TypeError or
      ValueError from the relevant conversion function.
    * ``streaming()`` would not have emitted a
      deprecation warning when called with an invalid argument.

.. _v3.21.1:

-------------------
3.21.1 - 2017-08-24
-------------------

This release fixes a bug where test failures that were the result of
an :func:`@example <hypothesis.example>` would print an extra stack trace before re-raising the
exception.

.. _v3.21.0:

-------------------
3.21.0 - 2017-08-23
-------------------

This release deprecates Hypothesis's strict mode, which turned Hypothesis's
deprecation warnings into errors. Similar functionality can be achieved
by using :func:`simplefilter('error', HypothesisDeprecationWarning) <python:warnings.simplefilter>`.

.. _v3.20.0:

-------------------
3.20.0 - 2017-08-22
-------------------

This release renames the relevant arguments on the
:func:`~hypothesis.strategies.datetimes`, :func:`~hypothesis.strategies.dates`,
:func:`~hypothesis.strategies.times`, and :func:`~hypothesis.strategies.timedeltas`
strategies to ``min_value`` and ``max_value``, to make them consistent with the
other strategies in the module.

The old argument names are still supported but will emit a deprecation warning
when used explicitly as keyword arguments. Arguments passed positionally will
go to the new argument names and are not deprecated.

.. _v3.19.3:

-------------------
3.19.3 - 2017-08-22
-------------------

This release provides a major overhaul to the internals of how Hypothesis
handles shrinking.

This should mostly be visible in terms of getting better examples for tests
which make heavy use of :func:`~hypothesis.strategies.composite`,
:func:`~hypothesis.strategies.data` or :ref:`flatmap <flatmap>` where the data
drawn depends a lot on previous choices, especially where size parameters are
affected. Previously Hypothesis would have struggled to reliably produce
good examples here. Now it should do much better. Performance should also be
better for examples with a non-zero ``min_size``.

You may see slight changes to example generation (e.g. improved example
diversity) as a result of related changes to internals, but they are unlikely
to be significant enough to notice.

.. _v3.19.2:

-------------------
3.19.2 - 2017-08-21
-------------------

This release fixes two bugs in :mod:`hypothesis.extra.numpy`:

* :func:`~hypothesis.extra.numpy.unicode_string_dtypes` didn't work at all due
  to an incorrect dtype specifier. Now it does.
* Various impossible conditions would have been accepted but would error when
  they fail to produced any example. Now they raise an explicit InvalidArgument
  error.

.. _v3.19.1:

-------------------
3.19.1 - 2017-08-21
-------------------

This is a bugfix release for :issue:`739`, where bounds for
:func:`~hypothesis.strategies.fractions` or floating-point
:func:`~hypothesis.strategies.decimals` were not properly converted to
integers before passing them to the integers strategy.
This excluded some values that should have been possible, and could
trigger internal errors if the bounds lay between adjacent integers.

You can now bound :func:`~hypothesis.strategies.fractions` with two
arbitrarily close fractions.

It is now an explicit error to supply a min_value, max_value, and
max_denominator to :func:`~hypothesis.strategies.fractions` where the value
bounds do not include a fraction with denominator at most max_denominator.

.. _v3.19.0:

-------------------
3.19.0 - 2017-08-20
-------------------

This release adds the :func:`~hypothesis.strategies.from_regex` strategy,
which generates strings that contain a match of a regular expression.

Thanks to Maxim Kulkin for creating the
`hypothesis-regex <https://github.com/maximkulkin/hypothesis-regex>`_
package and then helping to upstream it! (:issue:`662`)

.. _v3.18.5:

-------------------
3.18.5 - 2017-08-18
-------------------

This is a bugfix release for :func:`~hypothesis.strategies.integers`.
Previously the strategy would hit an internal assertion if passed non-integer
bounds for ``min_value`` and ``max_value`` that had no integers between them.
The strategy now raises InvalidArgument instead.

.. _v3.18.4:

-------------------
3.18.4 - 2017-08-18
-------------------

Release to fix a bug where mocks can be used as test runners under certain
conditions. Specifically, if a mock is injected into a test via pytest
fixtures or patch decorators, and that mock is the first argument in the
list, hypothesis will think it represents self and turns the mock
into a test runner.  If this happens, the affected test always passes
because the mock is executed instead of the test body. Sometimes, it
will also fail health checks.

Fixes :issue:`491` and a section of :issue:`198`.
Thanks to Ben Peterson for this bug fix.

.. _v3.18.3:

-------------------
3.18.3 - 2017-08-17
-------------------

This release should improve the performance of some tests which
experienced a slow down as a result of the :ref:`3.13.0 <v3.13.0>` release.

Tests most likely to benefit from this are ones that make extensive
use of ``min_size`` parameters, but others may see some improvement
as well.

.. _v3.18.2:

-------------------
3.18.2 - 2017-08-16
-------------------

This release fixes a bug introduced in :ref:`3.18.0 <v3.18.0>`. If the arguments
``whitelist_characters`` and ``blacklist_characters`` to
:func:`~hypothesis.strategies.characters` contained overlapping elements, then an
``InvalidArgument`` exception would be raised.

Thanks to Zac Hatfield-Dodds for reporting and fixing this.

.. _v3.18.1:

-------------------
3.18.1 - 2017-08-14
-------------------

This is a bug fix release to fix :issue:`780`, where
:func:`~hypothesis.strategies.sets` and similar would trigger health check
errors if their element strategy could only produce one element (e.g.
if it was :func:`~hypothesis.strategies.just`).

.. _v3.18.0:

-------------------
3.18.0 - 2017-08-13
-------------------

This is a feature release:

* :func:`~hypothesis.strategies.characters` now accepts
  ``whitelist_characters``, particular characters which will be added to those
  it produces. (:issue:`668`)
* A bug fix for the internal function ``_union_interval_lists()``, and a rename
  to ``_union_intervals()``. It now correctly handles all cases where intervals
  overlap, and it always returns the result as a tuple for tuples.

Thanks to Alex Willmer for these.

.. _v3.17.0:

-------------------
3.17.0 - 2017-08-07
-------------------

This release documents :ref:`the previously undocumented phases feature <phases>`,
making it part of the public API. It also updates how the example
database is used. Principally:

* A ``Phases.reuse`` argument will now correctly control whether examples
  from the database are run (it previously did exactly the wrong thing and
  controlled whether examples would be *saved*).
* Hypothesis will no longer try to rerun *all* previously failing examples.
  Instead it will replay the smallest previously failing example and a
  selection of other examples that are likely to trigger any other bugs that
  will found. This prevents a previous failure from dominating your tests
  unnecessarily.
* As a result of the previous change, Hypothesis will be slower about clearing
  out old examples from the database that are no longer failing (because it can
  only clear out ones that it actually runs).

.. _v3.16.1:

-------------------
3.16.1 - 2017-08-07
-------------------

This release makes an implementation change to how Hypothesis handles certain
internal constructs.

The main effect you should see is improvement to the behaviour and performance
of collection types, especially ones with a ``min_size`` parameter. Many cases
that would previously fail due to being unable to generate enough valid
examples will now succeed, and other cases should run slightly faster.

.. _v3.16.0:

-------------------
3.16.0 - 2017-08-04
-------------------

This release introduces a deprecation of the timeout feature. This results in
the following changes:

* Creating a settings object with an explicit timeout will emit a deprecation
  warning.
* If your test stops because it hits the timeout (and has not found a bug) then
  it will emit a deprecation warning.
* There is a new value ``unlimited`` which you can import from hypothesis.
  ``settings(timeout=unlimited)`` will *not* cause a deprecation warning.
* There is a new health check, ``hung_test``, which will trigger after a test
  has been running for five minutes if it is not suppressed.

.. _v3.15.0:

-------------------
3.15.0 - 2017-08-04
-------------------

This release deprecates two strategies, ``choices()`` and ``streaming()``.

Both of these are somewhat confusing to use and are entirely redundant since the
introduction of the :func:`~hypothesis.strategies.data` strategy for interactive
drawing in tests, and their use should be replaced with direct use of
:func:`~hypothesis.strategies.data` instead.

.. _v3.14.2:

-------------------
3.14.2 - 2017-08-03
-------------------

This fixes a bug where Hypothesis would not work correctly on Python 2.7 if you
had the :mod:`python:typing` module :pypi:`backport <typing>` installed.

.. _v3.14.1:

-------------------
3.14.1 - 2017-08-02
-------------------

This raises the maximum depth at which Hypothesis starts cutting off data
generation to a more reasonable value which it is harder to hit by accident.

This resolves (:issue:`751`), in which some examples which previously worked
would start timing out, but it will also likely improve the data generation
quality for complex data types.

.. _v3.14.0:

-------------------
3.14.0 - 2017-07-23
-------------------

Hypothesis now understands inline type annotations (:issue:`293`):

- If the target of :func:`~hypothesis.strategies.builds` has type annotations,
  a default strategy for missing required arguments is selected based on the
  type.  Type-based strategy selection will only override a default if you
  pass :const:`hypothesis.infer` as a keyword argument.

- If :func:`@given <hypothesis.given>` wraps a function with type annotations,
  you can pass :const:`~hypothesis.infer` as a keyword argument and the
  appropriate strategy will be substituted.

- You can check what strategy will be inferred for a type with the new
  :func:`~hypothesis.strategies.from_type` function.

- :func:`~hypothesis.strategies.register_type_strategy` teaches Hypothesis
  which strategy to infer for custom or unknown types.  You can provide a
  strategy, or for more complex cases a function which takes the type and
  returns a strategy.

.. _v3.13.1:

-------------------
3.13.1 - 2017-07-20
-------------------

This is a bug fix release for :issue:`514` - Hypothesis would continue running
examples after a :class:`~python:unittest.SkipTest` exception was raised,
including printing a falsifying example.  Skip exceptions from the standard
:mod:`python:unittest` module, and ``pytest``, ``nose``, or ``unittest2``
modules now abort the test immediately without printing output.

.. _v3.13.0:

-------------------
3.13.0 - 2017-07-16
-------------------

This release has two major aspects to it: The first is the introduction of
:func:`~hypothesis.strategies.deferred`, which allows more natural definition
of recursive (including mutually recursive) strategies.

The second is a number of engine changes designed to support this sort of
strategy better. These should have a knock-on effect of also improving the
performance of any existing strategies that currently generate a lot of data
or involve heavy nesting by reducing their typical example size.

.. _v3.12.0:

-------------------
3.12.0 - 2017-07-07
-------------------

This release makes some major internal changes to how Hypothesis represents
data internally, as a prelude to some major engine changes that should improve
data quality. There are no API changes, but it's a significant enough internal
change that a minor version bump seemed warranted.

User facing impact should be fairly mild, but includes:

* All existing examples in the database will probably be invalidated. Hypothesis
  handles this automatically, so you don't need to do anything, but if you see
  all your examples disappear that's why.
* Almost all data distributions have changed significantly. Possibly for the better,
  possibly for the worse. This may result in new bugs being found, but it may
  also result in Hypothesis being unable to find bugs it previously did.
* Data generation may be somewhat faster if your existing bottleneck was in
  draw_bytes (which is often the case for large examples).
* Shrinking will probably be slower, possibly significantly.

If you notice any effects you consider to be a significant regression, please
open an issue about them.

.. _v3.11.6:

-------------------
3.11.6 - 2017-06-19
-------------------

This release involves no functionality changes, but is the first to ship wheels
as well as an sdist.

.. _v3.11.5:

-------------------
3.11.5 - 2017-06-18
-------------------

This release provides a performance improvement to shrinking. For cases where
there is some non-trivial "boundary" value (e.g. the bug happens for all values
greater than some other value), shrinking should now be substantially faster.
Other types of bug will likely see improvements too.

This may also result in some changes to the quality of the final examples - it
may sometimes be better, but is more likely to get slightly worse in some edge
cases. If you see any examples where this happens in practice, please report
them.

.. _v3.11.4:

-------------------
3.11.4 - 2017-06-17
-------------------

This is a bugfix release: Hypothesis now prints explicit examples when
running in verbose mode.  (:issue:`313`)

.. _v3.11.3:

-------------------
3.11.3 - 2017-06-11
-------------------

This is a bugfix release: Hypothesis no longer emits a warning if you try to
use :func:`~hypothesis.strategies.sampled_from` with
:class:`python:collections.OrderedDict`.  (:issue:`688`)

.. _v3.11.2:

-------------------
3.11.2 - 2017-06-10
-------------------

This is a documentation release.  Several outdated snippets have been updated
or removed, and many cross-references are now hyperlinks.

.. _v3.11.1:

-------------------
3.11.1 - 2017-05-28
-------------------

This is a minor ergonomics release.  Tracebacks shown by pytest no longer
include Hypothesis internals for test functions decorated with :func:`@given <hypothesis.given>`.

.. _v3.11.0:

-------------------
3.11.0 - 2017-05-23
-------------------

This is a feature release, adding datetime-related strategies to the core strategies.

:func:`~hypothesis.extra.pytz.timezones` allows you to sample pytz timezones from
the Olsen database.  Use directly in a recipe for tz-aware datetimes, or
compose with :func:`~hypothesis.strategies.none` to allow a mix of aware and naive output.

The new :func:`~hypothesis.strategies.dates`, :func:`~hypothesis.strategies.times`,
:func:`~hypothesis.strategies.datetimes`, and :func:`~hypothesis.strategies.timedeltas`
strategies are all constrained by objects of their type.
This means that you can generate dates bounded by a single day
(i.e. a single date), or datetimes constrained to the microsecond.

:func:`~hypothesis.strategies.times` and :func:`~hypothesis.strategies.datetimes`
take an optional ``timezones=`` argument, which
defaults to :func:`~hypothesis.strategies.none` for naive times.  You can use our extra strategy
based on pytz, or roll your own timezones strategy with dateutil or even
the standard library.

The old ``dates``, ``times``, and ``datetimes`` strategies in
``hypothesis.extra.datetimes`` are deprecated in favor of the new
core strategies, which are more flexible and have no dependencies.

.. _v3.10.0:

-------------------
3.10.0 - 2017-05-22
-------------------

Hypothesis now uses :func:`python:inspect.getfullargspec` internally.
On Python 2, there are no visible changes.

On Python 3 :func:`@given <hypothesis.given>` and :func:`@composite <hypothesis.strategies.composite>`
now preserve :pep:`3107` annotations on the
decorated function.  Keyword-only arguments are now either handled correctly
(e.g. :func:`@composite <hypothesis.strategies.composite>`), or caught in validation instead of silently discarded
or raising an unrelated error later (e.g. :func:`@given <hypothesis.given>`).

.. _v3.9.1:

------------------
3.9.1 - 2017-05-22
------------------

This is a bugfix release: the default field mapping for a DateTimeField in the
Django extra now respects the ``USE_TZ`` setting when choosing a strategy.

.. _v3.9.0:

------------------
3.9.0 - 2017-05-19
------------------

This is feature release, expanding the capabilities of the
:func:`~hypothesis.strategies.decimals` strategy.

* The new (optional) ``places`` argument allows you to generate decimals with
  a certain number of places (e.g. cents, thousandths, satoshis).
* If allow_infinity is None, setting min_bound no longer excludes positive
  infinity and setting max_value no longer excludes negative infinity.
* All of ``NaN``, ``-Nan``, ``sNaN``, and ``-sNaN`` may now be drawn if
  allow_nan is True, or if allow_nan is None and min_value or max_value is None.
* min_value and max_value may be given as decimal strings, e.g. ``"1.234"``.


.. _v3.8.5:

------------------
3.8.5 - 2017-05-16
------------------

Hypothesis now imports :mod:`python:sqlite3` when a SQLite database is used, rather
than at module load, improving compatibility with Python implementations
compiled without SQLite support (such as BSD or Jython).

.. _v3.8.4:

------------------
3.8.4 - 2017-05-16
------------------

This is a compatibility bugfix release.  :func:`~hypothesis.strategies.sampled_from`
no longer raises a deprecation warning when sampling from an
:class:`python:enum.Enum`, as all enums have a reliable iteration order.

.. _v3.8.3:

------------------
3.8.3 - 2017-05-09
------------------

This release removes a version check for older versions of :pypi:`pytest` when using
the Hypothesis pytest plugin. The pytest plugin will now run unconditionally
on all versions of pytest. This breaks compatibility with any version of pytest
prior to 2.7.0 (which is more than two years old).

The primary reason for this change is that the version check was a frequent
source of breakage when pytest change their versioning scheme. If you are not
working on pytest itself and are not running a very old version of it, this
release probably doesn't affect you.

.. _v3.8.2:

------------------
3.8.2 - 2017-04-26
------------------

This is a code reorganisation release that moves some internal test helpers
out of the main source tree so as to not have changes to them trigger releases
in future.

.. _v3.8.1:

------------------
3.8.1 - 2017-04-26
------------------

This is a documentation release.  Almost all code examples are now doctests
checked in CI, eliminating stale examples.

.. _v3.8.0:

------------------
3.8.0 - 2017-04-23
------------------

This is a feature release, adding the :func:`~hypothesis.strategies.iterables` strategy, equivalent
to ``lists(...).map(iter)`` but with a much more useful repr.  You can use
this strategy to check that code doesn't accidentally depend on sequence
properties such as indexing support or repeated iteration.

.. _v3.7.4:

------------------
3.7.4 - 2017-04-22
------------------

This patch fixes a bug in :ref:`3.7.3 <v3.7.3>`, where using
:func:`@example <hypothesis.example>` and a pytest fixture in the same test
could cause the test to fail to fill the arguments, and throw a TypeError.

.. _v3.7.3:

------------------
3.7.3 - 2017-04-21
------------------

This release should include no user visible changes and is purely a refactoring
release. This modularises the behaviour of the core :func:`~hypothesis.given` function, breaking
it up into smaller and more accessible parts, but its actual behaviour should
remain unchanged.

.. _v3.7.2:

------------------
3.7.2 - 2017-04-21
------------------

This reverts an undocumented change in :ref:`3.7.1 <v3.7.1>` which broke installation on
debian stable: The specifier for the hypothesis[django] extra\_requires had
introduced a wild card, which was not supported on the default version of pip.

.. _v3.7.1:

------------------
3.7.1 - 2017-04-21
------------------

This is a bug fix and internal improvements release.

* In particular Hypothesis now tracks a tree of where it has already explored.
  This allows it to avoid some classes of duplicate examples, and significantly
  improves the performance of shrinking failing examples by allowing it to
  skip some shrinks that it can determine can't possibly work.
* Hypothesis will no longer seed the global random arbitrarily unless you have
  asked it to using :py:meth:`~hypothesis.strategies.random_module`
* Shrinking would previously have not worked correctly in some special cases
  on Python 2, and would have resulted in suboptimal examples.

.. _v3.7.0:

------------------
3.7.0 - 2017-03-20
------------------

This is a feature release.

New features:

* Rule based stateful testing now has an :func:`@invariant <hypothesis.stateful.invariant>` decorator that specifies
  methods that are run after init and after every step, allowing you to
  encode properties that should be true at all times. Thanks to Tom Prince for
  this feature.
* The :func:`~hypothesis.strategies.decimals` strategy now supports ``allow_nan`` and ``allow_infinity`` flags.
* There are :ref:`significantly more strategies available for numpy <hypothesis-numpy>`, including for
  generating arbitrary data types. Thanks to Zac Hatfield Dodds for this
  feature.
* When using the :func:`~hypothesis.strategies.data` strategy you can now add a label as an argument to
  ``draw()``, which will be printed along with the value when an example fails.
  Thanks to Peter Inglesby for this feature.

Bug fixes:

* Bug fix: :func:`~hypothesis.strategies.composite` now preserves functions' docstrings.
* The build is now reproducible and doesn't depend on the path you build it
  from. Thanks to Chris Lamb for this feature.
* numpy strategies for the void data type did not work correctly. Thanks to
  Zac Hatfield Dodds for this fix.

There have also been a number of performance optimizations:

* The :func:`~hypothesis.strategies.permutations` strategy is now significantly faster to use for large
  lists (the underlying algorithm has gone from O(n^2) to O(n)).
* Shrinking of failing test cases should have got significantly faster in
  some circumstances where it was previously struggling for a long time.
* Example generation now involves less indirection, which results in a small
  speedup in some cases (small enough that you won't really notice it except in
  pathological cases).


.. _v3.6.1:

------------------
3.6.1 - 2016-12-20
------------------

This release fixes a dependency problem and makes some small behind the scenes
improvements.

* The fake-factory dependency was renamed to faker. If you were depending on
  it through hypothesis[django] or hypothesis[fake-factory] without pinning it
  yourself then it would have failed to install properly. This release changes
  it so that hypothesis[fakefactory] (which can now also be installed as
  hypothesis[faker]) will install the renamed faker package instead.
* This release also removed the dependency of hypothesis[django] on
  hypothesis[fakefactory] - it was only being used for emails. These now use
  a custom strategy that isn't from fakefactory. As a result you should also
  see performance improvements of tests which generated User objects or other
  things with email fields, as well as better shrinking of email addresses.
* The distribution of code using nested calls to :func:`~hypothesis.strategies.one_of` or the ``|`` operator for
  combining strategies has been improved, as branches are now flattened to give
  a more uniform distribution.
* Examples using :func:`~hypothesis.strategies.composite` or ``.flatmap`` should now shrink better. In particular
  this will affect things which work by first generating a length and then
  generating that many items, which have historically not shrunk very well.

.. _v3.6.0:

------------------
3.6.0 - 2016-10-31
------------------

This release reverts Hypothesis to its old pretty printing of lambda functions
based on attempting to extract the source code rather than decompile the bytecode.
This is unfortunately slightly inferior in some cases and may result in you
occasionally seeing things like ``lambda x: <unknown>`` in statistics reports and
strategy reprs.

This removes the dependencies on uncompyle6, xdis and spark-parser.

The reason for this is that the new functionality was based on uncompyle6, which
turns out to introduce a hidden GPLed dependency - it in turn depended on xdis,
and although the library was licensed under the MIT license, it contained some
GPL licensed source code and thus should have been released under the GPL.

My interpretation is that Hypothesis itself was never in violation of the GPL
(because the license it is under, the Mozilla Public License v2, is fully
compatible with being included in a GPL licensed work), but I have not consulted
a lawyer on the subject. Regardless of the answer to this question, adding a
GPLed dependency will likely cause a lot of users of Hypothesis to inadvertently
be in violation of the GPL.

As a result, if you are running Hypothesis 3.5.x you really should upgrade to
this release immediately.

.. _v3.5.3:

------------------
3.5.3 - 2016-10-05
------------------

This is a bug fix release.

Bugs fixed:

* If the same test was running concurrently in two processes and there were
  examples already in the test database which no longer failed, Hypothesis
  would sometimes fail with a FileNotFoundError (IOError on Python 2) because
  an example it was trying to read was deleted before it was read. (:issue:`372`).
* Drawing from an :func:`~hypothesis.strategies.integers` strategy with both a min_value and a max_value
  would reject too many examples needlessly. Now it repeatedly redraws until
  satisfied. (:pull:`366`.  Thanks to Calen Pennington for the contribution).

.. _v3.5.2:

------------------
3.5.2 - 2016-09-24
------------------

This is a bug fix release.

* The Hypothesis pytest plugin broke pytest support for doctests. Now it doesn't.

.. _v3.5.1:

------------------
3.5.1 - 2016-09-23
------------------

This is a bug fix release.

* Hypothesis now runs cleanly in -B and -BB modes, avoiding mixing bytes and unicode.
* :class:`python:unittest.TestCase` tests would not have shown up in the new statistics mode. Now they
  do.
* Similarly, stateful tests would not have shown up in statistics and now they do.
* Statistics now print with pytest node IDs (the names you'd get in pytest verbose mode).

.. _v3.5.0:

------------------
3.5.0 - 2016-09-22
------------------

This is a feature release.

* :func:`~hypothesis.strategies.fractions` and :func:`~hypothesis.strategies.decimals` strategies now support min_value and max_value
  parameters. Thanks go to Anne Mulhern for the development of this feature.
* The Hypothesis pytest plugin now supports a ``--hypothesis-show-statistics`` parameter
  that gives detailed statistics about the tests that were run. Huge thanks to
  Jean-Louis Fuchs and Adfinis-SyGroup for funding the development of this feature.
* There is a new :func:`~hypothesis.event` function that can be used to add custom statistics.

Additionally there have been some minor bug fixes:

* In some cases Hypothesis should produce fewer duplicate examples (this will mostly
  only affect cases with a single parameter).
* :pypi:`pytest` command line parameters are now under an option group for Hypothesis (thanks
  to David Keijser for fixing this)
* Hypothesis would previously error if you used :pep:`3107` function annotations on your tests under
  Python 3.4.
* The repr of many strategies using lambdas has been improved to include the lambda body
  (this was previously supported in many but not all cases).

.. _v3.4.2:

------------------
3.4.2 - 2016-07-13
------------------

This is a bug fix release, fixing a number of problems with the settings system:

* Test functions defined using :func:`@given <hypothesis.given>` can now be called from other threads
  (:issue:`337`)
* Attempting to delete a settings property would previously have silently done
  the wrong thing. Now it raises an AttributeError.
* Creating a settings object with a custom database_file parameter was silently
  getting ignored and the default was being used instead. Now it's not.

.. _v3.4.1:

------------------
3.4.1 - 2016-07-07
------------------

This is a bug fix release for a single bug:

* On Windows when running two Hypothesis processes in parallel (e.g. using
  :pypi:`pytest-xdist`) they could race with each other and one would raise an exception
  due to the non-atomic nature of file renaming on Windows and the fact that you
  can't rename over an existing file. This is now fixed.

.. _v3.4.0:

------------------
3.4.0 - 2016-05-27
------------------

This release is entirely provided by `Lucas Wiman <https://github.com/lucaswiman>`_:

Strategies constructed by the Django extra
will now respect much more of Django's validations out of the box.
Wherever possible, :meth:`~django:django.db.models.Model.full_clean` should
succeed.

In particular:

* The max_length, blank and choices kwargs are now respected.
* Add support for DecimalField.
* If a field includes validators, the list of validators are used to filter the field strategy.

.. _v3.3.0:

------------------
3.3.0 - 2016-05-27
------------------

This release went wrong and is functionally equivalent to :ref:`3.2.0 <v3.2.0>`. Ignore it.

.. _v3.2.0:

------------------
3.2.0 - 2016-05-19
------------------

This is a small single-feature release:

* All tests using :func:`@given <hypothesis.given>` now fix the global random seed. This removes the health
  check for that. If a non-zero seed is required for the final falsifying
  example, it will be reported. Otherwise Hypothesis will assume randomization
  was not a significant factor for the test and be silent on the subject. If you
  use :func:`~hypothesis.strategies.random_module` this will continue to work and will always
  display the seed.

.. _v3.1.3:

------------------
3.1.3 - 2016-05-01
------------------

Single bug fix release

* Another charmap problem. In :ref:`3.1.2 <v3.1.2>` :func:`~hypothesis.strategies.text` and
  :func:`~hypothesis.strategies.characters` would break on systems
  which had ``/tmp`` mounted on a different partition than the Hypothesis storage
  directory (usually in home). This fixes that.

.. _v3.1.2:

------------------
3.1.2 - 2016-04-30
------------------

Single bug fix release:

* Anything which used a :func:`~hypothesis.strategies.text` or
  :func:`~hypothesis.strategies.characters` strategy was broken on Windows
  and I hadn't updated appveyor to use the new repository location so I didn't
  notice. This is now fixed and windows support should work correctly.

.. _v3.1.1:

------------------
3.1.1 - 2016-04-29
------------------

Minor bug fix release.

* Fix concurrency issue when running tests that use :func:`~hypothesis.strategies.text` from multiple
  processes at once (:issue:`302`, thanks to Alex Chan).
* Improve performance of code using :func:`~hypothesis.strategies.lists` with max_size (thanks to
  Cristi Cobzarenco).
* Fix install on Python 2 with ancient versions of pip so that it installs the
  :pypi:`enum34` backport (thanks to Donald Stufft for telling me how to do this).
* Remove duplicated __all__ exports from hypothesis.strategies (thanks to
  Piët Delport).
* Update headers to point to new repository location.
* Allow use of strategies that can't be used in ``find()``
  (e.g. ``choices()``) in stateful testing.


.. _v3.1.0:

------------------
3.1.0 - 2016-03-06
------------------

* Add a :func:`~hypothesis.strategies.nothing` strategy that never successfully generates values.
* :func:`~hypothesis.strategies.sampled_from` and :func:`~hypothesis.strategies.one_of`
  can both now be called with an empty argument
  list, in which case they also never generate any values.
* :func:`~hypothesis.strategies.one_of` may now be called with a single argument that is a collection of strategies
  as well as as varargs.
* Add a :func:`~hypothesis.strategies.runner` strategy which returns the instance of the current test object
  if there is one.
* 'Bundle' for RuleBasedStateMachine is now a normal(ish) strategy and can be used
  as such.
* Tests using RuleBasedStateMachine should now shrink significantly better.
* Hypothesis now uses a pretty-printing library internally, compatible with IPython's
  pretty printing protocol (actually using the same code). This may improve the quality
  of output in some cases.
* Add a 'phases' setting that allows more fine grained control over which parts of the
  process Hypothesis runs
* Add a suppress_health_check setting which allows you to turn off specific health checks
  in a fine grained manner.
* Fix a bug where lists of non fixed size would always draw one more element than they
  included. This mostly didn't matter, but if would cause problems with empty strategies
  or ones with side effects.
* Add a mechanism to the Django model generator to allow you to explicitly request the
  default value (thanks to Jeremy Thurgood for this one).

.. _v3.0.5:

------------------
3.0.5 - 2016-02-25
------------------

* Fix a bug where Hypothesis would now error on :pypi:`pytest` development versions.

.. _v3.0.4:

------------------
3.0.4 - 2016-02-24
------------------

* Fix a bug where Hypothesis would error when running on Python 2.7.3 or
  earlier because it was trying to pass a :class:`python:bytearray` object
  to :func:`python:struct.unpack` (which is only supported since 2.7.4).

.. _v3.0.3:

------------------
3.0.3 - 2016-02-23
------------------

* Fix version parsing of pytest to work with pytest release candidates
* More general handling of the health check problem where things could fail because
  of a cache miss - now one "free" example is generated before the start of the
  health check run.

.. _v3.0.2:

------------------
3.0.2 - 2016-02-18
------------------

* Under certain circumstances, strategies involving :func:`~hypothesis.strategies.text` buried inside some
  other strategy (e.g. ``text().filter(...)`` or ``recursive(text(), ...))`` would cause
  a test to fail its health checks the first time it ran. This was caused by having
  to compute some related data and cache it to disk. On travis or anywhere else
  where the ``.hypothesis`` directory was recreated this would have caused the tests
  to fail their health check on every run. This is now fixed for all the known cases,
  although there could be others lurking.

.. _v3.0.1:

------------------
3.0.1 - 2016-02-18
------------------

* Fix a case where it was possible to trigger an "Unreachable" assertion when
  running certain flaky stateful tests.
* Improve shrinking of large stateful tests by eliminating a case where it was
  hard to delete early steps.
* Improve efficiency of drawing :func:`binary(min_size=n, max_size=n) <hypothesis.strategies.binary>` significantly by
  provide a custom implementation for fixed size blocks that can bypass a lot
  of machinery.
* Set default home directory based on the current working directory at the
  point Hypothesis is imported, not whenever the function first happens to be
  called.

.. _v3.0.0:

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

* Addition of :func:`~hypothesis.strategies.data` strategy which allows you to draw arbitrary data interactively
  within the test.
* New "exploded" database format which allows you to more easily check the example
  database into a source repository while supporting merging.
* Better management of how examples are saved in the database.
* Health checks will now raise as errors when they fail. It was too easy to have
  the warnings be swallowed entirely.

New limitations:

* ``choices()`` and ``streaming()``
  strategies may no longer be used with ``find()``. Neither may
  :func:`~hypothesis.strategies.data` (this is the change that necessitated a major version bump).

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

.. _v2.0.0:

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


.. _v1.19.0:

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


.. _v1.18.1:

-------------------
1.18.1 - 2015-12-22
-------------------

Two behind the scenes changes:

* Hypothesis will no longer write generated code to the file system. This
  will improve performance on some systems (e.g. if you're using
  `PythonAnywhere <https://www.pythonanywhere.com/>`_ which is running your
  code from NFS) and prevent some annoying interactions with auto-restarting
  systems.
* Hypothesis will cache the creation of some strategies. This can significantly
  improve performance for code that uses flatmap or composite and thus has to
  instantiate strategies a lot.

.. _v1.18.0:

-------------------
1.18.0 - 2015-12-21
-------------------

Features:

* Tests and find are now explicitly seeded off the global random module. This
  means that if you nest one inside the other you will now get a health check
  error. It also means that you can control global randomization by seeding
  random.
* There is a new random_module() strategy which seeds the global random module
  for you and handles things so that you don't get a health check warning if
  you use it inside your tests.
* floats() now accepts two new arguments: allow\_nan and allow\_infinity. These
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

.. _v1.17.1:

-------------------
1.17.1 - 2015-12-16
-------------------

A small bug fix release, which fixes the fact that the 'note' function could
not be used on tests which used the @example decorator to provide explicit
examples.

.. _v1.17.0:

-------------------
1.17.0 - 2015-12-15
-------------------

This is actually the same release as 1.16.1, but 1.16.1 has been pulled because
it contains the following additional change that was not intended to be in a
patch  release (it's perfectly stable, but is a larger change that should have
required a minor version bump):

* Hypothesis will now perform a series of "health checks" as part of running
  your tests. These detect and warn about some common error conditions that
  people often run into which wouldn't necessarily have caused the test to fail
  but would cause e.g. degraded performance or confusing results.

.. _v1.16.1:

-------------------
1.16.1 - 2015-12-14
-------------------

Note: This release has been removed.

A small bugfix release that allows bdists for Hypothesis to be built
under 2.7 - the compat3.py file which had Python 3 syntax wasn't intended
to be loaded under Python 2, but when building a bdist it was. In particular
this would break running setup.py test.

.. _v1.16.0:

-------------------
1.16.0 - 2015-12-08
-------------------

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

.. _v1.15.0:

-------------------
1.15.0 - 2015-11-24
-------------------

A release with two new features.

* A 'characters' strategy for more flexible generation of text with particular
  character ranges and types, kindly contributed by `Alexander Shorin <https://github.com/kxepal>`_.
* Add support for preconditions to the rule based stateful testing. Kindly
  contributed by `Christopher Armstrong <https://github.com/radix>`_


.. _v1.14.0:

-------------------
1.14.0 - 2015-11-01
-------------------


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


.. _v1.13.0:

-------------------
1.13.0 - 2015-10-29
-------------------

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

.. _v1.12.0:

-------------------
1.12.0 - 2015-10-18
-------------------

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
* :pypi:`pytest` should no longer display the intermediate modules Hypothesis generates
  when running in verbose mode
* Hypothesis should now correctly handle printing objects with non-ascii reprs
  on python 3 when running in a locale that cannot handle ascii printing to
  stdout.
* Add a unique=True argument to lists(). This is equivalent to
  unique_by=lambda x: x, but offers a more convenient syntax.


.. _v1.11.4:

-------------------
1.11.4 - 2015-09-27
-------------------

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

.. _v1.11.3:

-------------------
1.11.3 - 2015-09-23
-------------------

* Better argument validation for datetimes() strategy - previously setting
  max_year < datetime.MIN_YEAR or min_year > datetime.MAX_YEAR would not have
  raised an InvalidArgument error and instead would have behaved confusingly.
* Compatibility with being run on pytest < 2.7 (achieved by disabling the
  plugin).

.. _v1.11.2:

-------------------
1.11.2 - 2015-09-23
-------------------

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

.. _v1.11.1:

-------------------
1.11.1 - 2015-09-16
-------------------

Bug fixes:

* When running Hypothesis tests in parallel (e.g. using pytest-xdist) there was a race
  condition caused by code generation.
* Example databases are now cached per thread so as to not use sqlite connections from
  multiple threads. This should make Hypothesis now entirely thread safe.
* floats() with only min_value or max_value set would have had a very bad distribution.
* Running on 3.5, Hypothesis would have emitted deprecation warnings because of use of
  inspect.getargspec

.. _v1.11.0:

-------------------
1.11.0 - 2015-08-31
-------------------

* text() with a non-string alphabet would have used the repr() of the the alphabet
  instead of its contexts. This is obviously silly. It now works with any sequence
  of things convertible to unicode strings.
* @given will now work on methods whose definitions contains no explicit positional
  arguments, only varargs (:issue:`118`).
  This may have some knock on effects because it means that @given no longer changes the
  argspec of functions other than by adding defaults.
* Introduction of new @composite feature for more natural definition of strategies you'd
  previously have used flatmap for.

.. _v1.10.6:

-------------------
1.10.6 - 2015-08-26
-------------------

Fix support for fixtures on Django 1.7.

.. _v1.10.4:

-------------------
1.10.4 - 2015-08-21
-------------------

Tiny bug fix release:

* If the database_file setting is set to None, this would have resulted in
  an error when running tests. Now it does the same as setting database to
  None.

.. _v1.10.3:

-------------------
1.10.3 - 2015-08-19
-------------------

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


.. _v1.10.2:

-------------------
1.10.2 - 2015-08-19
-------------------

This is a small bug fix release:

* star imports from hypothesis should now work correctly.
* example quality for examples using flatmap will be better, as the way it had
  previously been implemented was causing problems where Hypothesis was
  erroneously labelling some examples as being duplicates.

.. _v1.10.0:

-------------------
1.10.0 - 2015-08-04
-------------------

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

.. _v1.9.0:

------------------
1.9.0 - 2015-07-27
------------------

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

.. _v1.8.5:

------------------
1.8.5 - 2015-07-24
------------------

This contains no functionality changes but fixes a mistake made with
building the previous package that would have broken installation on
Windows.

.. _v1.8.4:

------------------
1.8.4 - 2015-07-20
------------------

Bugs fixed:

* When a call to floats() had endpoints which were not floats but merely
  convertible to one (e.g. integers), these would be included in the generated
  data which would cause it to generate non-floats.
* Splitting lambdas used in the definition of flatmap, map or filter over
  multiple lines would break the repr, which would in turn break their usage.


.. _v1.8.3:

------------------
1.8.3 - 2015-07-20
------------------

"Falsifying example" would not have been printed when the failure came from an
explicit example.

.. _v1.8.2:

------------------
1.8.2 - 2015-07-18
------------------

Another small bugfix release:

* When using ForkingTestCase you would usually not get the falsifying example
  printed if the process exited abnormally (e.g. due to os._exit).
* Improvements to the distribution of characters when using text() with a
  default alphabet. In particular produces a better distribution of ascii and
  whitespace in the alphabet.

.. _v1.8.1:

------------------
1.8.1 - 2015-07-17
------------------

This is a small release that contains a workaround for people who have
bad reprs returning non ascii text on Python 2.7. This is not a bug fix
for Hypothesis per se because that's not a thing that is actually supposed
to work, but Hypothesis leans more heavily on repr than is typical so it's
worth having a workaround for.

.. _v1.8.0:

------------------
1.8.0 - 2015-07-16
------------------

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


.. _v1.7.2:

------------------
1.7.2 - 2015-07-10
------------------

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

.. _v1.7.1:

------------------
1.7.1 - 2015-06-29
------------------

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


.. _v1.6.2:

------------------
1.6.2 - 2015-06-08
------------------

This is just a few small bug fixes:

* Size bounds were not validated for values for a binary() strategy when
  reading examples from the database.
* sampled\_from is now in __all__ in hypothesis.strategies
* floats no longer consider negative integers to be simpler than positive
  non-integers
* Small floating point intervals now correctly count members, so if you have a
  floating point interval so narrow there are only a handful of values in it,
  this will no longer cause an error when Hypothesis runs out of values.

.. _v1.6.1:

------------------
1.6.1 - 2015-05-21
------------------

This is a small patch release that fixes a bug where 1.6.0 broke the use
of flatmap with the deprecated API and assumed the passed in function returned
a SearchStrategy instance rather than converting it to a strategy.

.. _v1.6.0:

------------------
1.6.0 - 2015-05-21
------------------


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


.. _v1.5.0:

------------------
1.5.0 - 2015-05-14
------------------


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

.. _v1.4.0:

------------------
1.4.0 - 2015-05-04
------------------

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

.. _v1.3.0:

------------------
1.3.0 - 2015-05-22
------------------

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


.. _v1.2.1:

------------------
1.2.1 - 2015-04-16
------------------

A small patch release for a bug in the new executors feature. Tests which require
doing something to their result in order to fail would have instead reported as
flaky.

.. _v1.2.0:

------------------
1.2.0 - 2015-04-15
------------------

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

.. _v1.1.1:

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


.. _v1.1.0:

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


.. _v1.0.0:

------------------
1.0.0 - 2015-03-27
------------------

Codename: Blast-off!

There are no code changes in this release. This is precisely the 0.9.2 release
with some updated documentation.

.. _v0.9.2:

------------------
0.9.2 - 2015-03-26
------------------

Codename: T-1 days.

* floats_in_range would not actually have produced floats_in_range unless that
  range happened to be (0, 1). Fix this.

.. _v0.9.1:

------------------
0.9.1 - 2015-03-25
------------------

Codename: T-2 days.

* Fix a bug where if you defined a strategy using map on a lambda then the results would not be saved in the database.
* Significant performance improvements when simplifying examples using lists, strings or bounded integer ranges.

.. _v0.9.0:

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

.. _v0.7.2:

------------------
0.7.2 - 2015-03-22
------------------

Codename: Hygienic macros or bust

* You can now name an argument to @given 'f' and it won't break (:issue:`38`)
* strategy_test_suite is now named strategy_test_suite as the documentation claims and not in fact strategy_test_suitee
* Settings objects can now be used as a context manager to temporarily override the default values inside their context.


.. _v0.7.1:

------------------
0.7.1 - 2015-03-21
------------------

Codename: Point releases go faster

* Better string generation by parametrizing by a limited alphabet
* Faster string simplification - previously if simplifying a string with high range unicode characters it would try every unicode character smaller than that. This was pretty pointless. Now it stops after it's a short range (it can still reach smaller ones through recursive calls because of other simplifying operations).
* Faster list simplification by first trying a binary chop down the middle
* Simultaneous simplification of identical elements in a list. So if a bug only triggers when you have duplicates but you drew e.g. [-17, -17], this will now simplify to [0, 0].


.. _v0.7.0,:

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


.. _v0.6.0:

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

.. _v0.5.0:

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


.. _v0.4.3:

------------------
0.4.3 - 2015-02-05
------------------

Codename: TIL narrow Python builds are a thing

This just fixes the one bug.

* Apparently there is such a thing as a "narrow python build" and OS X ships with these by default
  for python 2.7. These are builds where you only have two bytes worth of unicode. As a result,
  generating unicode was completely broken on OS X. Fix this by only generating unicode codepoints
  in the range supported by the system.


.. _v0.4.2:

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


.. _v0.4.1:

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


.. _v0.4.0:

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

.. _v0.3.2:

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


.. _v0.3.1:

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


.. _v0.3.0:

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


.. _v0.2.2:

------------------
0.2.2 - 2015-01-08
------------------

* Fix an embarrassing complete failure of the installer caused by my being
  bad at version control


.. _v0.2.1:

------------------
0.2.1 - 2015-01-07
------------------

* Fix a bug in the new stateful testing feature where you could make
  __init__ a @requires method. Simplification would not always work if the
  prune method was able to successfully shrink the test.


.. _v0.2.0:

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


.. _v0.1.4:

------------------
0.1.4 - 2013-12-14
------------------

* Make verification runs time bounded with a configurable timeout


.. _v0.1.3:

------------------
0.1.3 - 2013-05-03
------------------

* Bugfix: Stateful testing behaved incorrectly with subclassing.
* Complex number support
* support for recursive strategies
* different error for hypotheses with unsatisfiable assumptions

.. _v0.1.2:

------------------
0.1.2 - 2013-03-24
------------------

* Bugfix: Stateful testing was not minimizing correctly and could
  throw exceptions.
* Better support for recursive strategies.
* Support for named tuples.
* Much faster integer generation.


.. _v0.1.1:

------------------
0.1.1 - 2013-03-24
------------------

* Python 3.x support via 2to3.
* Use new style classes (oops).


.. _v0.1.0:

------------------
0.1.0 - 2013-03-23
------------------

* Introduce stateful testing.
* Massive rewrite of internals to add flags and strategies.


.. _v0.0.5:

------------------
0.0.5 - 2013-03-13
------------------

* No changes except trying to fix packaging

.. _v0.0.4:

------------------
0.0.4 - 2013-03-13
------------------

* No changes except that I checked in a failing test case for 0.0.3
  so had to replace the release. Doh

.. _v0.0.3:

------------------
0.0.3 - 2013-03-13
------------------

* Improved a few internals.
* Opened up creating generators from instances as a general API.
* Test integration.

.. _v0.0.2:

------------------
0.0.2 - 2013-03-12
------------------

* Starting to tighten up on the internals.
* Change API to allow more flexibility in configuration.
* More testing.

.. _v0.0.1:

------------------
0.0.1 - 2013-03-10
------------------

* Initial release.
* Basic working prototype. Demonstrates idea, probably shouldn't be used.
