=========
Changelog
=========

This is a record of all past Hypothesis releases and what went into them,
in reverse chronological order. All previous releases should still be available
:pypi:`on PyPI <hypothesis>`.


Hypothesis 6.x
==============

.. only:: has_release_file

    --------------------
    Current pull request
    --------------------

    .. include:: ../RELEASE.rst

.. _v6.125.3:

--------------------
6.125.3 - 2025-02-11
--------------------

Improves sharing of some internal cache behavior.

.. _v6.125.2:

--------------------
6.125.2 - 2025-02-06
--------------------

Optimize performance (improves speed by ~5%) and clarify the wording in an error message.

.. _v6.125.1:

--------------------
6.125.1 - 2025-02-03
--------------------

Fixes a bug since around :ref:`version 6.124.4 <v6.124.4>` where we might have generated ``-0.0`` for ``st.floats(min_value=0.0)``, which is unsound.

.. _v6.125.0:

--------------------
6.125.0 - 2025-02-03
--------------------

Add 2024.12 to the list of recognized Array API versions in
``hypothesis.extra.array_api``.

.. _v6.124.9:

--------------------
6.124.9 - 2025-02-01
--------------------

Registration of experimental :ref:`alternative-backends` is now done via ``hypothesis.internal.conjecture.providers.AVAILABLE_PROVIDERS`` instead of ``hypothesis.internal.conjecture.data.AVAILABLE_PROVIDERS``.

.. _v6.124.8:

--------------------
6.124.8 - 2025-02-01
--------------------

Refactor some internals for better type hinting.

.. _v6.124.7:

--------------------
6.124.7 - 2025-01-25
--------------------

Internal renamings.

.. _v6.124.6:

--------------------
6.124.6 - 2025-01-25
--------------------

More work on internal type hints.

.. _v6.124.5:

--------------------
6.124.5 - 2025-01-25
--------------------

Internal refactoring to make some stateful internals easier to access.

.. _v6.124.4:

--------------------
6.124.4 - 2025-01-25
--------------------

Refactoring of our internal input generation. This shouldn't lead to any changes in the distribution of test inputs. If you notice any, please open an issue!

.. _v6.124.3:

--------------------
6.124.3 - 2025-01-24
--------------------

Some Hypothesis internals now use the number of choices as a yardstick of input size, rather than the entropy consumed by those choices. We don't expect this to cause significant behavioral changes.

.. _v6.124.2:

--------------------
6.124.2 - 2025-01-21
--------------------

Improves our internal caching logic for test cases.

.. _v6.124.1:

--------------------
6.124.1 - 2025-01-18
--------------------

:ref:`fuzz_one_input <fuzz_one_input>` is now implemented using an :ref:`alternative backend <alternative-backends>`. This brings the interpretation of the fuzzer-provided bytestring closer to the fuzzer mutations, allowing the mutations to work more reliably. We hope to use this backend functionality to improve fuzzing integration (see e.g. https://github.com/google/atheris/issues/20) in the future!

.. _v6.124.0:

--------------------
6.124.0 - 2025-01-16
--------------------

The :doc:`Hypothesis example database <database>` now uses a new internal format to store examples. This new format is not compatible with the previous format, so stored entries will not carry over.

The database is best thought of as a cache that may be invalidated at times. Instead of relying on it for correctness, we recommend using :obj:`@example <hypothesis.example>` to specify explicit examples. When using databases across environments (such as connecting a :class:`~hypothesis.database.GitHubArtifactDatabase` database in CI to your local environment), we recommend using the same version of Hypothesis for each where possible, for maximum reproducibility.

.. _v6.123.17:

---------------------
6.123.17 - 2025-01-13
---------------------

This patch improves certain corner cases for reporting of flaky errors
(:issue:`4183` and :issue:`4228`).

.. _v6.123.16:

---------------------
6.123.16 - 2025-01-13
---------------------

Improves an edge case in one of our integer and float shrinking passes.

.. _v6.123.15:

---------------------
6.123.15 - 2025-01-11
---------------------

Improves one of our shrinking passes for integers which require a constant relative difference to trigger the bug.

.. _v6.123.14:

---------------------
6.123.14 - 2025-01-11
---------------------

Avoid realizing symbolic values from :ref:`alternative-backends` when :obj:`~hypothesis.settings.verbosity` is ``verbose`` or higher.

.. _v6.123.13:

---------------------
6.123.13 - 2025-01-09
---------------------

More internal code refactoring.

.. _v6.123.12:

---------------------
6.123.12 - 2025-01-09
---------------------

:class:`~hypothesis.database.DirectoryBasedExampleDatabase` now creates files representing database entries atomically, avoiding a very brief intermediary state where a file could be created but not yet written to.

.. _v6.123.11:

---------------------
6.123.11 - 2025-01-09
---------------------

Internal code refactoring.

.. _v6.123.10:

---------------------
6.123.10 - 2025-01-09
---------------------

Fixes a bug caused by :ref:`alternative backends <alternative-backends>` raising ``hypothesis.errors.BackendCannotProceed`` in certain cases.

.. _v6.123.9:

--------------------
6.123.9 - 2025-01-08
--------------------

Add internal type hints to our pretty printer.

.. _v6.123.8:

--------------------
6.123.8 - 2025-01-08
--------------------

The shrinker contains a pass aimed at integers which are required to sum to a value. This patch extends that pass to floats as well.

.. _v6.123.7:

--------------------
6.123.7 - 2025-01-07
--------------------

Internal type hint additions and refactorings.

.. _v6.123.6:

--------------------
6.123.6 - 2025-01-07
--------------------

:func:`@reproduce_failure() <hypothesis.reproduce_failure>` now uses a newer internal interface to represent failures. As a reminder, this representation is not intended to be stable across versions or with respect to changes in the test.

.. _v6.123.5:

--------------------
6.123.5 - 2025-01-07
--------------------

Internal code refactoring for the typed choice sequence (:issue:`3921`). May have some neutral effect on shrinking.

.. _v6.123.4:

--------------------
6.123.4 - 2025-01-06
--------------------

This patch improves shrinking involving long strings or byte sequences whose value is not relevant to the failure.

.. _v6.123.3:

--------------------
6.123.3 - 2025-01-06
--------------------

This release further improves shrinking of strategies using :func:`~hypothesis.strategies.one_of`,
allowing the shrinker to more reliably move between branches of the strategy.

.. _v6.123.2:

--------------------
6.123.2 - 2024-12-27
--------------------

The shrinker now uses the typed choice sequence (:issue:`3921`) when ordering failing examples. As a result, Hypothesis may now report a different minimal failing example for some tests. We expect most cases to remain unchanged.

.. _v6.123.1:

--------------------
6.123.1 - 2024-12-24
--------------------

Our pytest plugin now emits a warning if you set Pytest's ``norecursedirs``
config option in such a way that the ``.hypothesis`` directory would be
searched for tests.  This reliably indicates that you've made a mistake
which slows down test collection, usually assuming that your configuration
extends the set of ignored patterns when it actually replaces them.
(:issue:`4200`)

.. _v6.123.0:

--------------------
6.123.0 - 2024-12-23
--------------------

:func:`~hypothesis.strategies.from_type` can now handle constructors with
required positional-only arguments if they have type annotations.  Previously,
we only passed arguments by keyword.

.. _v6.122.7:

--------------------
6.122.7 - 2024-12-23
--------------------

This patch lays some groundwork for migrating our internal representation to the typed choice sequence (:issue:`3921`)

.. _v6.122.6:

--------------------
6.122.6 - 2024-12-21
--------------------

This patch cleans up some internal code around clamping floats.

.. _v6.122.5:

--------------------
6.122.5 - 2024-12-20
--------------------

This release improves shrinking in some cases, especially for strategies using :func:`~hypothesis.strategies.one_of`.
This will typically improve shrinking speed and may in some cases improve the end result.

.. _v6.122.4:

--------------------
6.122.4 - 2024-12-19
--------------------

This patch improves generation performance for the provisional :func:`~hypothesis.provisional.domains` strategy, including its derivative strategies :func:`~hypothesis.provisional.urls` and :func:`~hypothesis.strategies.emails`.

.. _v6.122.3:

--------------------
6.122.3 - 2024-12-08
--------------------

This patch improves our error and warning messages.

- Add a warning for ``st.text("ascii")`` - you probably meant ``st.text(st.characters(codec="ascii"))``. Similarly for ``"utf-8"``.
- Recommend remedies in the error message of ``Unsatisfiable``.
- When ``@given`` errors because it was given an extra keyword argument, and the keyword matches a setting name like ``max_examples``, recommend ``@settings(max_examples=...)`` instead.

.. _v6.122.2:

--------------------
6.122.2 - 2024-12-08
--------------------

This patch updates some outdated external links in our documentation.

.. _v6.122.1:

--------------------
6.122.1 - 2024-12-01
--------------------

Fix :func:`~hypothesis.strategies.from_type`
on :class:`collections.abc.Callable` returning ``None``.

.. _v6.122.0:

--------------------
6.122.0 - 2024-11-29
--------------------

This release adds ``.span_start()`` and ``.span_end()`` methods
to our internal ``PrimitiveProvider`` interface, for use by
:ref:`alternative-backends`.

.. _v6.121.2:

--------------------
6.121.2 - 2024-11-29
--------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.121.1:

--------------------
6.121.1 - 2024-11-29
--------------------

This release brings back the old representation of :class:`hypothesis.stateful.Bundle`, reverting most changes of `PR #4124 <https://github.com/HypothesisWorks/hypothesis/pull/4124>`_.

.. _v6.121.0:

--------------------
6.121.0 - 2024-11-28
--------------------

This release adds :class:`~hypothesis.database.BackgroundWriteDatabase`, a new database backend which defers writes on the wrapped database to a background thread. This allows for low-overhead writes in performance-critical environments like :ref:`fuzz_one_input <fuzz_one_input>`.

.. _v6.120.0:

--------------------
6.120.0 - 2024-11-27
--------------------

* This release changes our input distribution for low ``max_examples``. Previously, we capped the size of inputs when generating at least the first 10 inputs, with the reasoning that early inputs to a property should be small. However, this meant properties with ``max_examples=10`` would consistent entirely of small inputs. This patch removes the hard lower bound so that inputs to these properties are more representative of the input space.
* When a user requests an interactive input via ``strategy.example``, we generate and cache a batch of 100 inputs, returning the first one. This can be expensive for large strategies or when only a few examples are needed. This release improves the speed of ``strategy.example`` by lowering the batch size to 10.

.. _v6.119.4:

--------------------
6.119.4 - 2024-11-22
--------------------

This patch fixes a bug since :ref:`v6.99.13` where only interactively-generated values (via ``data.draw``) would be reported in the ``arguments`` field of our :doc:`observability output <observability>`. Now, all values are reported.

.. _v6.119.3:

--------------------
6.119.3 - 2024-11-17
--------------------

Hypothesis collects coverage information during the ``shrink`` and ``explain`` :ref:`phases <phases>` in order to show a more informative error message. On 3.12+, this uses :mod:`sys.monitoring`. This patch improves the performance of coverage collection on 3.12+ by disabling events we don't need.

.. _v6.119.2:

--------------------
6.119.2 - 2024-11-17
--------------------

This patch refactors some internals to prepare for future work using our IR (:issue:`3921`).

.. _v6.119.1:

--------------------
6.119.1 - 2024-11-15
--------------------

This patch migrates some more internals (around generating novel inputs) to the IR layer (:issue:`3921`).

.. _v6.119.0:

--------------------
6.119.0 - 2024-11-15
--------------------

This release improves Hypothesis' handling of ExceptionGroup - it's now able to detect marker detections if they're inside a  group and attempts to resolve them. Note that this handling is still a work in progress and might not handle edge cases optimally. Please open issues if you encounter any problems or unexpected behavior with it.

.. _v6.118.9:

--------------------
6.118.9 - 2024-11-15
--------------------

Internal refactorings in preparation for upcoming changes.

.. _v6.118.8:

--------------------
6.118.8 - 2024-11-12
--------------------

Internal renamings.

.. _v6.118.7:

--------------------
6.118.7 - 2024-11-10
--------------------

This patch removes some ``# type: ignore`` comments following a :pypi:`mypy` update.

.. _v6.118.6:

--------------------
6.118.6 - 2024-11-10
--------------------

When Hypothesis replays examples from its test database that it knows were previously fully shrunk it will no longer try to shrink them again.

This should significantly speed up development workflows for slow tests, as the shrinking could contribute a significant delay when rerunning the tests.

In some rare cases this may cause minor reductions in example quality. This was considered an acceptable tradeoff for the improved test runtime.

.. _v6.118.5:

--------------------
6.118.5 - 2024-11-10
--------------------

This patch avoids computing some string representations we won't need,
giving a small speedup (part of :issue:`4139`).

.. _v6.118.4:

--------------------
6.118.4 - 2024-11-10
--------------------

This patch migrates the optimisation algorithm for :ref:`targeted property-based testing <targeted-search>` to our IR layer (:issue:`3921`). This should result in moderately different (and hopefully improved) exploration behavior in tests which use :func:`hypothesis.target`.

.. _v6.118.3:

--------------------
6.118.3 - 2024-11-10
--------------------

This patch adds more type hints to internal Hypothesis code.

.. _v6.118.2:

--------------------
6.118.2 - 2024-11-09
--------------------

This patch migrates the :obj:`~hypothesis.Phase.explain` :ref:`phase <phases>` to our IR layer (:issue:`3921`). This should improve both its speed and precision.

.. _v6.118.1:

--------------------
6.118.1 - 2024-11-09
--------------------

This patch updates some internals around how we determine an input is too large to finish generating.

.. _v6.118.0:

--------------------
6.118.0 - 2024-11-08
--------------------

The :func:`~hypothesis.provisional.urls` strategy no longer generates
URLs where the port number is 0.

This change is motivated by the idea that the generated URLs should, at least in
theory, be possible to fetch. The port number 0 is special; if a server binds to
port 0, the kernel will allocate an unused, and non-zero, port instead. That
means that it's not possible for a server to actually be listening on port 0.
This motivation is briefly described in the documentation for
:func:`~hypothesis.provisional.urls`.

Fixes :issue:`4157`.

Thanks to @gmacon for this contribution!

.. _v6.117.0:

--------------------
6.117.0 - 2024-11-07
--------------------

This changes the behaviour of settings profiles so that if you reregister the currently loaded profile it will automatically reload it. Previously you would have had to load it again.

In particular this means that if you register a "ci" profile, it will automatically be used when Hypothesis detects you are running on CI.

.. _v6.116.0:

--------------------
6.116.0 - 2024-11-01
--------------------

Hypothesis now detects if it is running on a CI server and provides better default settings for running on CI in this case.

.. _v6.115.6:

--------------------
6.115.6 - 2024-10-30
--------------------

This patch changes the priority order of pretty printing logic so that a user
provided pretty printing method will always be used in preference to e.g.
printing it like a dataclass.

.. _v6.115.5:

--------------------
6.115.5 - 2024-10-23
--------------------

This patch restores diversity to the outputs of
:func:`from_type(type) <hypothesis.strategies.from_type>` (:issue:`4144`).

.. _v6.115.4:

--------------------
6.115.4 - 2024-10-23
--------------------

This release improves pretty printing of nested classes to include the outer class name in their printed representation.

.. _v6.115.3:

--------------------
6.115.3 - 2024-10-16
--------------------

This patch fixes a regression from :ref:`version 6.115.2 <v6.115.2>` where generating values from :func:`~hypothesis.strategies.integers` with certain values for ``min_value`` and ``max_value`` would error.

.. _v6.115.2:

--------------------
6.115.2 - 2024-10-14
--------------------

This release improves integer shrinking by folding the endpoint upweighting for :func:`~hypothesis.strategies.integers` into the ``weights`` parameter of our IR (:issue:`3921`).

If you maintain an alternative backend as part of our (for now explicitly unstable) :ref:`alternative-backends`, this release changes the type of the ``weights`` parameter to ``draw_integer`` and may be a breaking change for you.

.. _v6.115.1:

--------------------
6.115.1 - 2024-10-14
--------------------

This patch improves the performance of :func:`~hypothesis.strategies.from_type` with
`pydantic.types.condate <https://docs.pydantic.dev/latest/api/types/#pydantic.types.condate>`__
(:issue:`4000`).

.. _v6.115.0:

--------------------
6.115.0 - 2024-10-12
--------------------

This improves the formatting of dataclasses and attrs classes when printing
falsifying examples.

.. _v6.114.1:

--------------------
6.114.1 - 2024-10-10
--------------------

This patch upgrades remaining type annotations to Python 3.9 syntax.

.. _v6.114.0:

--------------------
6.114.0 - 2024-10-09
--------------------

This release drops support for Python 3.8, `which reached end of life on
2024-10-07 <https://devguide.python.org/versions/>`__.

.. _v6.113.0:

--------------------
6.113.0 - 2024-10-09
--------------------

This release adds ``hypothesis.errors.BackendCannotProceed``, an unstable API
for use by :ref:`alternative-backends`.

.. _v6.112.5:

--------------------
6.112.5 - 2024-10-08
--------------------

This release fixes a regression where :class:`hypothesis.stateful.Bundle` did not work properly with :ref:`flatmap <flatmap>` functionality (:issue:`4128`).

.. _v6.112.4:

--------------------
6.112.4 - 2024-10-06
--------------------

This patch tweaks the paths in ``@example(...)`` patches, so that
both ``git apply`` and ``patch`` will work by default.

.. _v6.112.3:

--------------------
6.112.3 - 2024-10-05
--------------------

This release refactors internals of :class:`hypothesis.stateful.Bundle` to have a more consistent representation internally.

.. _v6.112.2:

--------------------
6.112.2 - 2024-09-29
--------------------

This patch fixes an internal error when the ``__context__``
attribute of a raised exception leads to a cycle (:issue:`4115`).

.. _v6.112.1:

--------------------
6.112.1 - 2024-09-13
--------------------

This patch removes a now-incorrect internal assertion about numpy's typing after recent numpy changes (currently only in numpy's nightly release).

.. _v6.112.0:

--------------------
6.112.0 - 2024-09-05
--------------------

This release adds support for variable-width bytes in our IR layer (:issue:`3921`), which should mean improved performance anywhere you use :func:`~hypothesis.strategies.binary`. If you maintain an alternative backend as part of our (for now explicitly unstable) :ref:`alternative-backends`, this release changes the ``draw_*`` interface and may be a breaking change for you.

.. _v6.111.2:

--------------------
6.111.2 - 2024-08-24
--------------------

This patch contains some internal code cleanup.  There is no user-visible change.

.. _v6.111.1:

--------------------
6.111.1 - 2024-08-15
--------------------

This patch improves shrinking in cases involving 'slips' from one strategy to another. Highly composite strategies are the most likely to benefit from this change.

This patch also reduces the range of :class:`python:datetime.datetime` generated by :func:`~hypothesis.extra.django.from_model` in order to avoid https://code.djangoproject.com/ticket/35683.

.. _v6.111.0:

--------------------
6.111.0 - 2024-08-11
--------------------

:ref:`alternative-backends` can now implement ``.observe_test_case()``
and ``observe_information_message()`` methods, to record backend-specific
metadata and messages in our :doc:`observability output <observability>`
(:issue:`3845` and `hypothesis-crosshair#22
<https://github.com/pschanely/hypothesis-crosshair/issues/22>`__).

.. _v6.110.2:

--------------------
6.110.2 - 2024-08-11
--------------------

Support ``__default__`` field of :obj:`~python:typing.TypeVar`
and support the same from :pypi:`typing-extensions`
in :func:`~hypothesis.strategies.from_type`.

.. _v6.110.1:

--------------------
6.110.1 - 2024-08-08
--------------------

Add better error message for :obj:`!~python:typing.TypeIs` types
in :func:`~hypothesis.strategies.from_type`.

.. _v6.110.0:

--------------------
6.110.0 - 2024-08-07
--------------------

Support :obj:`~python:typing.LiteralString`
in :func:`~hypothesis.strategies.from_type`.

.. _v6.109.1:

--------------------
6.109.1 - 2024-08-07
--------------------

This patch makes progress towards adding type hints to our internal conjecture engine (:issue:`3074`).

.. _v6.109.0:

--------------------
6.109.0 - 2024-08-07
--------------------

This release allows using :obj:`~python:typing.Annotated`
and :obj:`!ReadOnly` types
for :class:`~python:typing.TypedDict` value types
with :func:`~hypothesis.strategies.from_type`.

.. _v6.108.10:

---------------------
6.108.10 - 2024-08-06
---------------------

This patch fixes compatibility with :pypi:`attrs==24.1.0 <attrs>`
on the nightly build of CPython, 3.14.0 pre-alpha (:issue:`4067`).

.. _v6.108.9:

--------------------
6.108.9 - 2024-08-05
--------------------

This patch removes an assertion which was in fact possible in rare circumstances involving a small number of very large draws.

.. _v6.108.8:

--------------------
6.108.8 - 2024-08-04
--------------------

This patch improves our example generation performance by adjusting our internal cache implementation.

.. _v6.108.7:

--------------------
6.108.7 - 2024-08-04
--------------------

This patch improves our pretty-printer for unusual numbers.

- Signalling NaNs are now represented by using the :mod:`struct` module
  to show the exact value by converting from a hexadecimal integer

- CPython `limits integer-to-string conversions
  <https://docs.python.org/3/library/stdtypes.html#integer-string-conversion-length-limitation>`__
  to mitigate DDOS attacks.  We now use hexadecimal for very large
  integers, and include underscore separators for integers with ten
  or more digits.

.. _v6.108.6:

--------------------
6.108.6 - 2024-08-04
--------------------

This patch improves generation speed in some cases by avoiding pretty-printing overhead for non-failing examples.

.. _v6.108.5:

--------------------
6.108.5 - 2024-07-28
--------------------

This patch fixes a rare internal error when using :func:`~hypothesis.strategies.integers` with a high number of examples and certain ``{min, max}_value`` parameters (:pull:`4059`).

.. _v6.108.4:

--------------------
6.108.4 - 2024-07-22
--------------------

This patch addresses the issue of hypothesis potentially accessing
mocked ``time.perf_counter`` during test execution (:issue:`4051`).

.. _v6.108.3:

--------------------
6.108.3 - 2024-07-22
--------------------

Minor internal-only cleanups to some error-handling and reporting code.

.. _v6.108.2:

--------------------
6.108.2 - 2024-07-15
--------------------

This patch disables :func:`hypothesis.target` on alternative
backends where it would not work.

.. _v6.108.1:

--------------------
6.108.1 - 2024-07-14
--------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.108.0:

--------------------
6.108.0 - 2024-07-13
--------------------

This patch changes most Flaky errors to use an ExceptionGroup, which
makes the representation of these errors easier to understand.

.. _v6.107.0:

--------------------
6.107.0 - 2024-07-13
--------------------

The ``alphabet=`` argument to :func:`~hypothesis.strategies.from_regex`
now accepts unions of :func:`~hypothesis.strategies.characters` and
:func:`~hypothesis.strategies.sampled_from` strategies, in addition to
accepting each individually.

This patch also fixes a bug where ``text(...).filter(re.compile(...).match)``
could generate non-matching instances if the regex pattern contained ``|``
(:issue:`4008`).

.. _v6.106.1:

--------------------
6.106.1 - 2024-07-12
--------------------

This patch improves our pretty-printer (:issue:`4037`).

It also fixes the codemod for ``HealthCheck.all()`` from
:ref:`version 6.72 <v6.72.0>`, which was instead trying to
fix ``Healthcheck.all()`` - note the lower-case ``c``!
Since our tests had the same typo, it all looked good...
until :issue:`4030`.

.. _v6.106.0:

--------------------
6.106.0 - 2024-07-12
--------------------

This release improves support for unions of :pypi:`numpy` dtypes such as
``np.float64 | np.complex128`` in :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.extra.numpy.arrays` (:issue:`4041`).

.. _v6.105.2:

--------------------
6.105.2 - 2024-07-12
--------------------

This patch improves the reporting of certain flaky errors.

.. _v6.105.1:

--------------------
6.105.1 - 2024-07-07
--------------------

This patch iterates on our experimental support for alternative backends (:ref:`alternative-backends`). See :pull:`4029` for details.

.. _v6.105.0:

--------------------
6.105.0 - 2024-07-04
--------------------

This release improves support for Django 5.0, and drops support for end-of-life Django versions (< 4.2).

Thanks to Joshua Munn for this contribution.

.. _v6.104.4:

--------------------
6.104.4 - 2024-07-04
--------------------

Clean up internal cache implementation.

.. _v6.104.3:

--------------------
6.104.3 - 2024-07-04
--------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.104.2:

--------------------
6.104.2 - 2024-06-29
--------------------

This patch fixes an issue when realizing symbolics with our experimental :obj:`~hypothesis.settings.backend` setting.

.. _v6.104.1:

--------------------
6.104.1 - 2024-06-25
--------------------

Improves internal test coverage.

.. _v6.104.0:

--------------------
6.104.0 - 2024-06-24
--------------------

This release adds strategies for Django's ``ModelChoiceField`` and
``ModelMultipleChoiceField`` (:issue:`4010`).

Thanks to Joshua Munn for this contribution.

.. _v6.103.5:

--------------------
6.103.5 - 2024-06-24
--------------------

Fixes and reinstates full coverage of internal tests, which was accidentally
disabled in :pull:`3935`.

Closes :issue:`4003`.

.. _v6.103.4:

--------------------
6.103.4 - 2024-06-24
--------------------

This release prevents a race condition inside internal cache implementation.

.. _v6.103.3:

--------------------
6.103.3 - 2024-06-24
--------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.103.2:

--------------------
6.103.2 - 2024-06-14
--------------------

This patch improves our deduplication tracking across all strategies (:pull:`4007`). Hypothesis is now less likely to generate the same input twice.

.. _v6.103.1:

--------------------
6.103.1 - 2024-06-05
--------------------

Account for time spent in garbage collection during tests, to avoid
flaky ``DeadlineExceeded`` errors as seen in :issue:`3975`.

Also fixes overcounting of stateful run times,
a minor observability bug dating to :ref:`version 6.98.9 <v6.98.9>`
(:pull:`3890`).

.. _v6.103.0:

--------------------
6.103.0 - 2024-05-29
--------------------

This release migrates the shrinker to our new internal representation, called the IR layer (:pull:`3962`). This improves the shrinker's performance in the majority of cases. For example, on the Hypothesis test suite, shrinking is a median of 1.38x faster.

It is possible this release regresses performance while shrinking certain strategies. If you encounter strategies which reliably shrink more slowly than they used to (or shrink slowly at all), please open an issue!

You can read more about the IR layer at :issue:`3921`.

.. _v6.102.6:

--------------------
6.102.6 - 2024-05-23
--------------------

This patch fixes one of our shrinking passes getting into a rare ``O(n)`` case instead of ``O(log(n))``.

.. _v6.102.5:

--------------------
6.102.5 - 2024-05-22
--------------------

This patch fixes some introspection errors new in Python 3.11.9 and
3.13.0b1, for the Ghostwriter and :func:`~hypothesis.strategies.from_type`.

.. _v6.102.4:

--------------------
6.102.4 - 2024-05-15
--------------------

Internal developer documentation, no user-visible changes.

.. _v6.102.3:

--------------------
6.102.3 - 2024-05-15
--------------------

This patch improves our shrinking of unique collections, such as  :func:`~hypothesis.strategies.dictionaries`,
:func:`~hypothesis.strategies.sets`, and :func:`~hypothesis.strategies.lists` with ``unique=True``.

.. _v6.102.2:

--------------------
6.102.2 - 2024-05-15
--------------------

This patch fixes a rare internal error when generating very large elements from strategies (:issue:`3874`).

.. _v6.102.1:

--------------------
6.102.1 - 2024-05-13
--------------------

This patch fixes an overly strict internal type assertion.

.. _v6.102.0:

--------------------
6.102.0 - 2024-05-13
--------------------

This release improves our support for the :pypi:`annotated-types` iterable
``GroupedMetadata`` protocol.  In order to treat the elements "as if they
had been unpacked", if one such element is a :class:`~hypothesis.strategies.SearchStrategy`
we now resolve to that strategy.  Previously, we treated this as an unknown
filter predicate.

We expect this to be useful for libraries implementing custom metadata -
instead of requiring downstream integration, they can implement the protocol
and yield a lazily-created strategy.  Doing so only if Hypothesis is in
:obj:`sys.modules` gives powerful integration with no runtime overhead
or extra dependencies.

.. _v6.101.0:

--------------------
6.101.0 - 2024-05-13
--------------------

The :func:`~hypothesis.extra.django.from_model` function currently
tries to create a strategy for :obj:`~django:django.db.models.AutoField`
fields if they don't have :attr:`~django:django.db.models.Field.auto_created`
set to `True`.  The docs say it's supposed to skip all
:obj:`~django:django.db.models.AutoField` fields, so this patch updates
the code to do what the docs say (:issue:`3978`).

.. _v6.100.8:

--------------------
6.100.8 - 2024-05-13
--------------------

This patch adds some internal type annotations (:issue:`3074`).
Thanks to Andrew Sansom for his contribution!

.. _v6.100.7:

--------------------
6.100.7 - 2024-05-12
--------------------

This patch fixes a rare internal error when using :func:`~hypothesis.strategies.integers` with a high ``max_examples`` setting (:issue:`3974`).

.. _v6.100.6:

--------------------
6.100.6 - 2024-05-10
--------------------

This patch improves our internal caching logic. We don't expect it to result in any performance improvements (yet!).

.. _v6.100.5:

--------------------
6.100.5 - 2024-05-06
--------------------

This patch turns off a check in :func:`~hypothesis.register_random` for possibly
unreferenced RNG instances on the free-threaded build of CPython 3.13 because
this check has a much higher false positive rate in the free-threaded build
(:issue:`3965`).

Thanks to Nathan Goldbaum for this patch.

.. _v6.100.4:

--------------------
6.100.4 - 2024-05-05
--------------------

This patch turns off a warning for functions decorated with
:func:`typing.overload` and then :func:`~hypothesis.strategies.composite`,
although only in that order (:issue:`3970`).

.. _v6.100.3:

--------------------
6.100.3 - 2024-05-04
--------------------

This patch fixes a significant slowdown when using the :func:`~hypothesis.stateful.precondition` decorator in some cases, due to expensive repr formatting internally (:issue:`3963`).

.. _v6.100.2:

--------------------
6.100.2 - 2024-04-28
--------------------

Explicitly cast :obj:`numpy.finfo.smallest_normal` to builtin `float` in
preparation for the :pypi:`numpy==2.0 <numpy>` release (:issue:`3950`)

.. _v6.100.1:

--------------------
6.100.1 - 2024-04-08
--------------------

This patch improve a rare error message for flaky tests (:issue:`3940`).

.. _v6.100.0:

--------------------
6.100.0 - 2024-03-31
--------------------

The :func:`~hypothesis.extra.numpy.from_dtype` function no longer generates
``NaT`` ("not-a-time") values for the ``datetime64`` or ``timedelta64`` dtypes
if passed ``allow_nan=False`` (:issue:`3943`).

.. _v6.99.13:

--------------------
6.99.13 - 2024-03-24
--------------------

This patch includes the :obj:`~hypothesis.settings.backend` setting in the
``how_generated`` field of our :doc:`observability output <observability>`.

.. _v6.99.12:

--------------------
6.99.12 - 2024-03-23
--------------------

If you were running Python 3.13 (currently in alpha) with :pypi:`pytest-xdist`
and then attempted to pretty-print a ``lambda`` functions which was created
using the :func:`eval` builtin, it would have raised an AssertionError.
Now you'll get ``"lambda ...: <unknown>"``, as expected.

.. _v6.99.11:

--------------------
6.99.11 - 2024-03-20
--------------------

This release improves an internal invariant.

.. _v6.99.10:

--------------------
6.99.10 - 2024-03-20
--------------------

This patch fixes Hypothesis sometimes raising a ``Flaky`` error when generating collections of unique floats containing ``nan``. See :issue:`3926` for more details.

.. _v6.99.9:

-------------------
6.99.9 - 2024-03-19
-------------------

This patch continues our work on refactoring the shrinker (:issue:`3921`).

.. _v6.99.8:

-------------------
6.99.8 - 2024-03-18
-------------------

This patch continues our work on refactoring shrinker internals (:issue:`3921`).

.. _v6.99.7:

-------------------
6.99.7 - 2024-03-18
-------------------

This release resolves :py:exc:`PermissionError` that come from
creating databases on inaccessible paths.

.. _v6.99.6:

-------------------
6.99.6 - 2024-03-14
-------------------

This patch starts work on refactoring our shrinker internals. There is no user-visible change.

.. _v6.99.5:

-------------------
6.99.5 - 2024-03-12
-------------------

This patch fixes a longstanding performance problem in stateful testing (:issue:`3618`),
where state machines which generated a substantial amount of input for each step would
hit the maximum amount of entropy and then fail with an ``Unsatisfiable`` error.

We now stop taking additional steps when we're approaching the entropy limit,
which neatly resolves the problem without touching unaffected tests.

.. _v6.99.4:

-------------------
6.99.4 - 2024-03-11
-------------------

Fix regression caused by using :pep:`696` default in TypeVar with Python 3.13.0a3.

.. _v6.99.3:

-------------------
6.99.3 - 2024-03-11
-------------------

This patch further improves the type annotations in :mod:`hypothesis.extra.numpy`.

.. _v6.99.2:

-------------------
6.99.2 - 2024-03-10
-------------------

Simplify the type annotation of :func:`~hypothesis.extra.pandas.column` and
:func:`~hypothesis.extra.pandas.columns` by using :pep:`696` to avoid overloading.

.. _v6.99.1:

-------------------
6.99.1 - 2024-03-10
-------------------

This patch implements type annotations for :func:`~hypothesis.extra.pandas.column`.

.. _v6.99.0:

-------------------
6.99.0 - 2024-03-09
-------------------

This release adds the **experimental and unstable** :obj:`~hypothesis.settings.backend`
setting.  See :ref:`alternative-backends` for details.

.. _v6.98.18:

--------------------
6.98.18 - 2024-03-09
--------------------

This patch fixes :issue:`3900`, a performance regression for
:func:`~hypothesis.extra.numpy.arrays` due to the interaction of
:ref:`v6.98.12` and :ref:`v6.97.1`.

.. _v6.98.17:

--------------------
6.98.17 - 2024-03-04
--------------------

This patch improves the type annotations in :mod:`hypothesis.extra.numpy`,
which makes inferred types more precise for both :pypi:`mypy` and
:pypi:`pyright`, and fixes some strict-mode errors on the latter.

Thanks to Jonathan Plasse for reporting and fixing this in :pull:`3889`!

.. _v6.98.16:

--------------------
6.98.16 - 2024-03-04
--------------------

This patch paves the way for future shrinker improvements. There is no user-visible change.

.. _v6.98.15:

--------------------
6.98.15 - 2024-02-29
--------------------

This release adds support for the Array API's `2023.12 release
<https://data-apis.org/array-api/2023.12/>`_ via the ``api_version`` argument in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`. The API additions
and modifications in the ``2023.12`` spec do not necessitate any changes in the
Hypothesis strategies, hence there is no distinction between a ``2022.12`` and
``2023.12`` strategies namespace.

.. _v6.98.14:

--------------------
6.98.14 - 2024-02-29
--------------------

This patch adjusts the printing of bundle values to correspond
with their names when using stateful testing.

.. _v6.98.13:

--------------------
6.98.13 - 2024-02-27
--------------------

This patch implements filter-rewriting for :func:`~hypothesis.strategies.text`
and :func:`~hypothesis.strategies.binary` with the :meth:`~re.Pattern.search`,
:meth:`~re.Pattern.match`, or :meth:`~re.Pattern.fullmatch` method of a
:func:`re.compile`\ d regex.

.. _v6.98.12:

--------------------
6.98.12 - 2024-02-25
--------------------

This patch implements filter-rewriting for most length filters on some
additional collection types (:issue:`3795`), and fixes several latent
bugs where unsatisfiable or partially-infeasible rewrites could trigger
internal errors.

.. _v6.98.11:

--------------------
6.98.11 - 2024-02-24
--------------------

This patch makes stateful testing somewhat less likely to get stuck
when there are only a few possible rules.

.. _v6.98.10:

--------------------
6.98.10 - 2024-02-22
--------------------

This patch :pep:`adds a note <678>` to errors which occur while drawing from
a strategy, to make it easier to tell why your test failed in such cases.

.. _v6.98.9:

-------------------
6.98.9 - 2024-02-20
-------------------

This patch ensures that :doc:`observability <observability>` outputs include
an informative repr for :class:`~hypothesis.stateful.RuleBasedStateMachine`
stateful tests, along with more detailed timing information.

.. _v6.98.8:

-------------------
6.98.8 - 2024-02-18
-------------------

This patch improves :doc:`the Ghostwriter <ghostwriter>` for binary operators.

.. _v6.98.7:

-------------------
6.98.7 - 2024-02-18
-------------------

This patch improves import-detection in :doc:`the Ghostwriter <ghostwriter>`
(:issue:`3884`), particularly for :func:`~hypothesis.strategies.from_type`
and strategies from ``hypothesis.extra.*``.

.. _v6.98.6:

-------------------
6.98.6 - 2024-02-15
-------------------

This patch clarifies the documentation on stateful testing (:issue:`3511`).

.. _v6.98.5:

-------------------
6.98.5 - 2024-02-14
-------------------

This patch improves argument-to-json conversion for :doc:`observability <observability>`
output.  Checking for a ``.to_json()`` method on the object *before* a few other
options like dataclass support allows better user control of the process (:issue:`3880`).

.. _v6.98.4:

-------------------
6.98.4 - 2024-02-12
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.98.3:

-------------------
6.98.3 - 2024-02-08
-------------------

This patch fixes an error when generating :doc:`observability <observability>` reports involving large (``n > 1e308``) integers.

.. _v6.98.2:

-------------------
6.98.2 - 2024-02-05
-------------------

This patch refactors some internals. There is no user-visible change.

.. _v6.98.1:

-------------------
6.98.1 - 2024-02-05
-------------------

This release improves our distribution of generated values for all strategies, by doing a better job of tracking which values we have generated before and avoiding generating them again.

For example, ``st.lists(st.integers())`` previously generated ~5 each of ``[]`` ``[0]`` in 100 examples. In this release, each of ``[]`` and ``[0]`` are generated ~1-2 times each.

.. _v6.98.0:

-------------------
6.98.0 - 2024-02-05
-------------------

This release deprecates use of the global random number generator while drawing
from a strategy, because this makes test cases less diverse and prevents us
from reporting minimal counterexamples (:issue:`3810`).

If you see this new warning, you can get a quick fix by using
:func:`~hypothesis.strategies.randoms`; or use more idiomatic strategies
:func:`~hypothesis.strategies.sampled_from`, :func:`~hypothesis.strategies.floats`,
:func:`~hypothesis.strategies.integers`, and so on.

Note that the same problem applies to e.g. ``numpy.random``, but
for performance reasons we only check the stdlib :mod:`random` module -
ignoring even other sources passed to :func:`~hypothesis.register_random`.

.. _v6.97.6:

-------------------
6.97.6 - 2024-02-04
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.97.5:

-------------------
6.97.5 - 2024-02-03
-------------------

This patch adds some :doc:`observability information <observability>`
about how many times predicates in :func:`~hypothesis.assume` or
:func:`~hypothesis.stateful.precondition` were satisfied, so that
downstream tools can warn you if some were *never* satisfied by
any test case.

.. _v6.97.4:

-------------------
6.97.4 - 2024-01-31
-------------------

This patch improves formatting and adds some cross-references to our docs.

.. _v6.97.3:

-------------------
6.97.3 - 2024-01-30
-------------------

Internal test refactoring.

.. _v6.97.2:

-------------------
6.97.2 - 2024-01-30
-------------------

This patch slightly changes how we replay examples from
:doc:`the database <database>`: if the behavior of the saved example has
changed, we now keep running the test case instead of aborting at the size
of the saved example.  While we know it's not the *same* example, we might
as well continue running the test!

Because we now finish running a few more examples for affected tests, this
might be a slight slowdown - but correspondingly more likely to find a bug.

We've also applied similar tricks to the :ref:`target phase <phases>`, where
they are a pure performance improvement for affected tests.

.. _v6.97.1:

-------------------
6.97.1 - 2024-01-27
-------------------

Improves the performance of the :func:`~hypothesis.extra.numpy.arrays`
strategy when generating unique values.

.. _v6.97.0:

-------------------
6.97.0 - 2024-01-25
-------------------

Changes the distribution of :func:`~hypothesis.strategies.sampled_from` when
sampling from a :class:`~python:enum.Flag`. Previously, no-flags-set values would
never be generated, and all-flags-set values would be unlikely for large enums.
With this change, the distribution is more uniform in the number of flags set.

.. _v6.96.4:

-------------------
6.96.4 - 2024-01-23
-------------------

This patch slightly refactors some internals. There is no user-visible change.

.. _v6.96.3:

-------------------
6.96.3 - 2024-01-22
-------------------

This patch fixes a spurious warning about slow imports when ``HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY`` was set.

.. _v6.96.2:

-------------------
6.96.2 - 2024-01-21
-------------------

This patch refactors some more internals, continuing our work on supporting alternative backends (:issue:`3086`). There is no user-visible change.

.. _v6.96.1:

-------------------
6.96.1 - 2024-01-18
-------------------

Fix a spurious warning seen when running pytest's test
suite, caused by never realizing we got out of
initialization due to imbalanced hook calls.

.. _v6.96.0:

-------------------
6.96.0 - 2024-01-17
-------------------

Warns when constructing a `repr` that is overly long. This can
happen by accident if stringifying arbitrary strategies, and
is expensive in time and memory. The associated deferring of
these long strings in :func:`~hypothesis.strategies.sampled_from`
should also lead to improved performance.

.. _v6.95.0:

-------------------
6.95.0 - 2024-01-17
-------------------

This release adds the ability to pass any object to :func:`~hypothesis.note`, instead of just strings. The pretty-printed representation of the object will be used.

See also :issue:`3843`.

.. _v6.94.0:

-------------------
6.94.0 - 2024-01-16
-------------------

This release avoids creating a ``.hypothesis`` directory when using
:func:`~hypothesis.strategies.register_type_strategy` (:issue:`3836`),
and adds warnings for plugins which do so by other means or have
other unintended side-effects.

.. _v6.93.2:

-------------------
6.93.2 - 2024-01-15
-------------------

This patch improves :doc:`observability <observability>` reports by moving
timing information from ``metadata`` to a new ``timing`` key, and supporting
conversion of additional argument types to json rather than string reprs
via a ``.to_json()`` method (including e.g. Pandas dataframes).

Additionally, the :obj:`~hypothesis.HealthCheck.too_slow` health check will
now report *which* strategies were slow, e.g. for strategies a, b, c, ...::

        count | fraction |    slowest draws (seconds)
    a |    3  |     65%  |      --      --      --   0.357,  2.000
    b |    8  |     16%  |   0.100,  0.100,  0.100,  0.111,  0.123
    c |    3  |      8%  |      --      --   0.030,  0.050,  0.200
    (skipped 2 rows of fast draws)

.. _v6.93.1:

-------------------
6.93.1 - 2024-01-15
-------------------

This patch refactors some internals, continuing our work on supporting alternative backends
(:issue:`3086`). There is no user-visible change.

.. _v6.93.0:

-------------------
6.93.0 - 2024-01-13
-------------------

The :func:`~hypothesis.extra.lark.from_lark` strategy now accepts an ``alphabet=``
argument, which is passed through to :func:`~hypothesis.strategies.from_regex`,
so that you can e.g. constrain the generated strings to a particular codec.

In support of this feature, :func:`~hypothesis.strategies.from_regex` will avoid
generating optional parts which do not fit the alphabet.  For example,
``from_regex(r"abc|def", alphabet="abcd")`` was previously an error, and will now
generate only ``'abc'``.  Cases where there are no valid strings remain an error.

.. _v6.92.9:

-------------------
6.92.9 - 2024-01-12
-------------------

This patch refactors some internals, continuing our work on supporting alternative backends (:issue:`3086`). There is no user-visible change.

.. _v6.92.8:

-------------------
6.92.8 - 2024-01-11
-------------------

This patch adds a :ref:`test statistics <statistics>` event when a generated example is rejected via :func:`assume <hypothesis.assume>`.

This may also help with distinguishing ``gave_up`` examples in :doc:`observability <observability>` (:issue:`3827`).

.. _v6.92.7:

-------------------
6.92.7 - 2024-01-10
-------------------

This introduces the rewriting of length filters on some collection strategies (:issue:`3791`).

Thanks to Reagan Lee for implementing this feature!

.. _v6.92.6:

-------------------
6.92.6 - 2024-01-08
-------------------

If a test uses :func:`~hypothesis.strategies.sampled_from` on a sequence of
strategies, and raises a ``TypeError``, we now :pep:`add a note <678>` asking
whether you meant to use :func:`~hypothesis.strategies.one_of`.

Thanks to Vince Reuter for suggesting and implementing this hint!

.. _v6.92.5:

-------------------
6.92.5 - 2024-01-08
-------------------

This patch registers explicit strategies for a handful of builtin types,
motivated by improved introspection in PyPy 7.3.14 triggering existing
internal warnings.
Thanks to Carl Friedrich Bolz-Tereick for helping us work out what changed!

.. _v6.92.4:

-------------------
6.92.4 - 2024-01-08
-------------------

This patch fixes an error when writing :doc:`observability <observability>` reports without a pre-existing ``.hypothesis`` directory.

.. _v6.92.3:

-------------------
6.92.3 - 2024-01-08
-------------------

This patch adds a new environment variable ``HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_NOCOVER``,
which turns on :doc:`observability <observability>` data collection without collecting
code coverage data, which may be faster on Python 3.11 and earlier.

Thanks to Harrison Goldstein for reporting and fixing :issue:`3821`.

.. _v6.92.2:

-------------------
6.92.2 - 2023-12-27
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.92.1:

-------------------
6.92.1 - 2023-12-16
-------------------

This patch fixes a bug introduced in :ref:`version 6.92.0 <v6.92.0>`,
where using the :func:`~hypothesis.strategies.data` strategy would fail
to draw a :func:`~python:dataclasses.dataclass` with a
:class:`~python:collections.defaultdict` field.  This was due to a bug
in the standard library which `was fixed in 3.12
<https://github.com/python/cpython/pull/32056>`__, so we've vendored the fix.

.. _v6.92.0:

-------------------
6.92.0 - 2023-12-10
-------------------

This release adds an experimental :wikipedia:`observability <Observability_(software)>`
mode.  :doc:`You can read the docs about it here <observability>`.

.. _v6.91.2:

-------------------
6.91.2 - 2023-12-10
-------------------

This patch refactors some more internals, continuing our work on supporting alternative backends (:issue:`3086`). There is no user-visible change.

.. _v6.91.1:

-------------------
6.91.1 - 2023-12-08
-------------------

This patch fixes an issue where :func:`~hypothesis.strategies.builds` could not be used with :pypi:`attrs` objects that defined private attributes (i.e. attributes with a leading underscore). See also :issue:`3791`.

This patch also adds support more generally for using :func:`~hypothesis.strategies.builds` with attrs' ``alias`` parameter, which was previously unsupported.

This patch increases the minimum required version of attrs to 22.2.0.

.. _v6.91.0:

-------------------
6.91.0 - 2023-11-27
-------------------

This release adds an optional ``payload`` argument to :func:`hypothesis.event`,
so that you can clearly express the difference between the label and the value
of an observation.  :ref:`statistics` will still summarize it as a string, but
future observability options can preserve the distinction.

.. _v6.90.1:

-------------------
6.90.1 - 2023-11-27
-------------------

This patch supports assigning ``settings = settings(...)`` as a class attribute
on a subclass of a ``.TestCase`` attribute of a :class:`~hypothesis.stateful.RuleBasedStateMachine`.
Previously, this did nothing at all.

.. code-block: python

    # works as of this release
    class TestMyStatefulMachine(MyStatefulMachine.TestCase):
        settings = settings(max_examples=10000)

    # the old way still works, but it's more verbose.
    MyStateMachine.TestCase.settings = settings(max_examples=10000)
    class TestMyStatefulMachine(MyStatefulMachine.TestCase):
        pass

Thanks to Joey Tran for reporting these settings-related edge cases in stateful testing.

.. _v6.90.0:

-------------------
6.90.0 - 2023-11-20
-------------------

This release makes it an error to assign ``settings = settings(...)``
as a class attribute on a :class:`~hypothesis.stateful.RuleBasedStateMachine`.
This has never had any effect, and it should be used as a decorator instead:

.. code-block: python

    class BadMachine(RuleBasedStateMachine):
        """This doesn't do anything, and is now an error!"""
        settings = settings(derandomize=True)

    @settings(derandomize=True)
    class GoodMachine(RuleBasedStateMachine):
        """This is the right way to do it :-)"""

.. _v6.89.1:

-------------------
6.89.1 - 2023-11-19
-------------------

This patch refactors some internals.  There is no user-visible change,
but we hope to improve performance and unlock support for alternative
backends such as :pypi:`symbolic execution with crosshair <crosshair-tool>`
in future (:issue:`3086`).

Thanks to Liam DeVoe for this fantastic contribution!

.. _v6.89.0:

-------------------
6.89.0 - 2023-11-16
-------------------

This release teaches :func:`~hypothesis.strategies.from_type` to handle constraints
implied by the :pypi:`annotated-types` package - as used by e.g. :pypi:`pydantic`.
This is usually efficient, but falls back to filtering in a few remaining cases.

Thanks to Viicos for :pull:`3780`!

.. _v6.88.4:

-------------------
6.88.4 - 2023-11-13
-------------------

This patch adds a warning when :func:`@st.composite <hypothesis.strategies.composite>`
wraps a function annotated as returning a :class:`~hypothesis.strategies.SearchStrategy`,
since this is usually an error (:issue:`3786`).  The function should return a value,
and the decorator will convert it to a function which returns a strategy.

.. _v6.88.3:

-------------------
6.88.3 - 2023-11-05
-------------------

This patch refactors ``from_type(typing.Tuple)``, allowing
:func:`~hypothesis.strategies.register_type_strategy` to take effect
for tuples instead of being silently ignored (:issue:`3750`).

Thanks to Nick Collins for reporting and extensive work on this issue.

.. _v6.88.2:

-------------------
6.88.2 - 2023-11-05
-------------------

This patch improves the speed of the explain phase on python 3.12+, by using the new
:mod:`sys.monitoring` module to collect coverage, instead of :obj:`sys.settrace`.

Thanks to Liam DeVoe for :pull:`3776`!

.. _v6.88.1:

-------------------
6.88.1 - 2023-10-16
-------------------

This patch improves :func:`~hypothesis.strategies.register_type_strategy` when used with ``tuple`` subclasses,
by preventing them from being interpreted as generic and provided to strategies like ``st.from_type(Sequence[int])``
(:issue:`3767`).

.. _v6.88.0:

-------------------
6.88.0 - 2023-10-15
-------------------

This release allows strategy-generating functions registered with
:func:`~hypothesis.strategies.register_type_strategy` to conditionally not
return a strategy, by returning :data:`NotImplemented` (:issue:`3767`).

.. _v6.87.4:

-------------------
6.87.4 - 2023-10-12
-------------------

When :func:`~hypothesis.strategies.randoms` was called with ``use_true_randoms=False``,
calling ``r.sample([], 0)`` would result in an error,
when it should have returned an empty sequence to agree with the normal behaviour of
:func:`random.sample`. This fixes that discrepancy (:issue:`3765`).

.. _v6.87.3:

-------------------
6.87.3 - 2023-10-06
-------------------

This patch ensures that the :ref:`hypothesis codemod <codemods>` CLI
will print a warning instead of stopping with an internal error if
one of your files contains invalid syntax (:issue:`3759`).

.. _v6.87.2:

-------------------
6.87.2 - 2023-10-06
-------------------

This patch makes some small changes to our NumPy integration to ensure forward
compatibility.  Thanks to Mateusz Sokół for :pull:`3761`.

.. _v6.87.1:

-------------------
6.87.1 - 2023-10-01
-------------------

Fixes :issue:`3755`, where an internal condition turns out
to be reachable after all.

.. _v6.87.0:

-------------------
6.87.0 - 2023-09-25
-------------------

This release deprecates use of :func:`~hypothesis.assume` and ``reject()``
outside of property-based tests, because these functions work by raising a
special exception (:issue:`3743`).  It also fixes some type annotations
(:issue:`3753`).

.. _v6.86.2:

-------------------
6.86.2 - 2023-09-18
-------------------

Hotfix for :issue:`3747`, a bug in explain mode which is so rare that
we missed it in six months of dogfooding.  Thanks to :pypi:`mygrad`
for discovering and promptly reporting this!

.. _v6.86.1:

-------------------
6.86.1 - 2023-09-17
-------------------

This patch improves the documentation of :obj:`@example(...).xfail() <hypothesis.example.xfail>`
by adding a note about :pep:`614`, similar to :obj:`@example(...).via() <hypothesis.example.via>`,
and adds a warning when a strategy generates a test case which seems identical to
one provided by an xfailed example.

.. _v6.86.0:

-------------------
6.86.0 - 2023-09-17
-------------------

This release enables the :obj:`~hypothesis.Phase.explain` :ref:`phase <phases>`
by default.  We hope it helps you to understand *why* your failing tests have
failed!

.. _v6.85.1:

-------------------
6.85.1 - 2023-09-16
-------------------

This patch switches some of our type annotations to use :obj:`typing.Literal`
when only a few specific values are allowed, such as UUID or IP address versions.

.. _v6.85.0:

-------------------
6.85.0 - 2023-09-16
-------------------

This release deprecates the old whitelist/blacklist arguments
to :func:`~hypothesis.strategies.characters`, in favor of
include/exclude arguments which more clearly describe their
effects on the set of characters which can be generated.

You can :ref:`use Hypothesis' codemods <codemods>` to automatically
upgrade to the new argument names.  In a future version, the old
names will start to raise a ``DeprecationWarning``.

.. _v6.84.3:

-------------------
6.84.3 - 2023-09-10
-------------------

This patch automatically disables the :obj:`~hypothesis.HealthCheck.differing_executors`
health check for methods which are also pytest parametrized tests, because
those were mostly false alarms (:issue:`3733`).

.. _v6.84.2:

-------------------
6.84.2 - 2023-09-06
-------------------

Building on recent releases, :func:`~hypothesis.strategies.characters`
now accepts _any_ ``codec=``, not just ``"utf-8"`` and ``"ascii"``.

This includes standard codecs from the :mod:`codecs` module and their
aliases, platform specific and user-registered codecs if they are
available, and `python-specific text encodings
<https://docs.python.org/3/library/codecs.html#python-specific-encodings>`__
(but not text transforms or binary transforms).

.. _v6.84.1:

-------------------
6.84.1 - 2023-09-05
-------------------

This patch by Reagan Lee makes ``st.text(...).filter(str.isidentifier)``
return an efficient custom strategy (:issue:`3480`).

.. _v6.84.0:

-------------------
6.84.0 - 2023-09-04
-------------------

The :func:`~hypothesis.strategies.from_regex` strategy now takes an optional
``alphabet=characters(codec="utf-8")`` argument for unicode strings, like
:func:`~hypothesis.strategies.text`.

This offers more and more-consistent control over the generated strings,
removing previously-hard-coded limitations.  With ``fullmatch=False`` and
``alphabet=characters()``, surrogate characters are now possible in leading
and trailing text as well as the body of the match.  Negated character classes
such as ``[^A-Z]`` or ``\S`` had a hard-coded exclusion of control characters
and surrogate characters; now they permit anything in ``alphabet=`` consistent
with the class, and control characters are permitted by default.

.. _v6.83.2:

-------------------
6.83.2 - 2023-09-04
-------------------

Add a health check that detects if the same test is executed
several times by :ref:`different executors<custom-function-execution>`.
This can lead to difficult-to-debug problems such as :issue:`3446`.

.. _v6.83.1:

-------------------
6.83.1 - 2023-09-03
-------------------

Pretty-printing of failing examples can now use functions registered with
:func:`IPython.lib.pretty.for_type` or :func:`~IPython.lib.pretty.for_type_by_name`,
as well as restoring compatibility with ``_repr_pretty_`` callback methods
which were accidentally broken in :ref:`version 6.61.2 <v6.61.2>` (:issue:`3721`).

.. _v6.83.0:

-------------------
6.83.0 - 2023-09-01
-------------------

Adds a new ``codec=`` option in :func:`~hypothesis.strategies.characters`, making it
convenient to produce only characters which can be encoded as ``ascii`` or ``utf-8``
bytestrings.

Support for other codecs will be added in a future release.

.. _v6.82.7:

-------------------
6.82.7 - 2023-08-28
-------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.82.6:

-------------------
6.82.6 - 2023-08-20
-------------------

This patch enables and fixes many more of :pypi:`ruff`\ 's lint rules.

.. _v6.82.5:

-------------------
6.82.5 - 2023-08-18
-------------------

Fixes the error message for missing ``[cli]`` extra.

.. _v6.82.4:

-------------------
6.82.4 - 2023-08-12
-------------------

This patch ensures that we always close the download connection in
:class:`~hypothesis.database.GitHubArtifactDatabase`.

.. _v6.82.3:

-------------------
6.82.3 - 2023-08-08
-------------------

We can now pretty-print combinations of *zero* :class:`enum.Flag`
values, like ``SomeFlag(0)``, which has never worked before.

.. _v6.82.2:

-------------------
6.82.2 - 2023-08-06
-------------------

This patch fixes pretty-printing of combinations of :class:`enum.Flag`
values, which was previously an error (:issue:`3709`).

.. _v6.82.1:

-------------------
6.82.1 - 2023-08-05
-------------------

Improve shrinking of floats in narrow regions that don't cross an integer
boundary. Closes :issue:`3357`.

.. _v6.82.0:

-------------------
6.82.0 - 2023-07-20
-------------------

:func:`~hypothesis.strategies.from_regex` now supports the atomic grouping
(``(?>...)``) and possessive quantifier (``*+``, ``++``, ``?+``, ``{m,n}+``)
syntax `added in Python 3.11 <https://docs.python.org/3/whatsnew/3.11.html#re>`__.

Thanks to Cheuk Ting Ho for implementing this!

.. _v6.81.2:

-------------------
6.81.2 - 2023-07-15
-------------------

If the :envvar:`HYPOTHESIS_NO_PLUGINS` environment variable is set, we'll avoid
:ref:`loading plugins <entry-points>` such as `the old Pydantic integration
<https://docs.pydantic.dev/latest/integrations/hypothesis/>`__ or
`HypoFuzz' CLI options <https://hypofuzz.com/docs/quickstart.html#running-hypothesis-fuzz>`__.

This is probably only useful for our own self-tests, but documented in case it might
help narrow down any particularly weird bugs in complex environments.

.. _v6.81.1:

-------------------
6.81.1 - 2023-07-11
-------------------

Fixes some lingering issues with inference of recursive types
in :func:`~hypothesis.strategies.from_type`. Closes :issue:`3525`.

.. _v6.81.0:

-------------------
6.81.0 - 2023-07-10
-------------------

This release further improves our ``.patch``-file support from
:ref:`version 6.75 <v6.75.0>`, skipping duplicates, tests which use
:func:`~hypothesis.strategies.data` (and don't support
:obj:`@example() <hypothesis.example>`\ ), and various broken edge-cases.

Because :pypi:`libCST <libcst>` has released version 1.0 which uses the native parser
by default, we no longer set the ``LIBCST_PARSER_TYPE=native`` environment
variable.  If you are using an older version, you may need to upgrade or
set this envvar for yourself.

.. _v6.80.1:

-------------------
6.80.1 - 2023-07-06
-------------------

This patch updates some internal code for selftests.
There is no user-visible change.

.. _v6.80.0:

-------------------
6.80.0 - 2023-06-27
-------------------

This release drops support for Python 3.7, `which reached end of life on
2023-06-27 <https://devguide.python.org/versions/>`__.

.. _v6.79.4:

-------------------
6.79.4 - 2023-06-27
-------------------

Fixes occasional recursion-limit-exceeded errors when validating
deeply nested strategies. Closes: :issue:`3671`

.. _v6.79.3:

-------------------
6.79.3 - 2023-06-26
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.79.2:

-------------------
6.79.2 - 2023-06-22
-------------------

Improve the type rendered in :func:`~hypothesis.strategies.from_type`,
which improves the coverage of Ghostwriter.

.. _v6.79.1:

-------------------
6.79.1 - 2023-06-19
-------------------

We now test against Python 3.12 beta in CI, and this patch
fixes some new deprecations.

.. _v6.79.0:

-------------------
6.79.0 - 2023-06-17
-------------------

This release changes :func:`~hypothesis.strategies.register_type_strategy`
for compatibility with :pep:`585`: we now store only a single strategy or
resolver function which is used for both the builtin and the ``typing``
module version of each type (:issue:`3635`).

If you previously relied on registering separate strategies for e.g.
``list`` vs ``typing.List``, you may need to use explicit strategies
rather than inferring them from types.

.. _v6.78.3:

-------------------
6.78.3 - 2023-06-15
-------------------

This release ensures that Ghostwriter does not use the deprecated aliases
for the ``collections.abc`` classes in ``collections``.

.. _v6.78.2:

-------------------
6.78.2 - 2023-06-13
-------------------

This patch improves Ghostwriter's use of qualified names for re-exported
functions and classes, and avoids importing useless :obj:`~typing.TypeVar`\ s.

.. _v6.78.1:

-------------------
6.78.1 - 2023-06-12
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.78.0:

-------------------
6.78.0 - 2023-06-11
-------------------

New input validation for :func:`~hypothesis.strategies.recursive`
will raise an error rather than hanging indefinitely if passed
invalid ``max_leaves=`` arguments.

.. _v6.77.0:

-------------------
6.77.0 - 2023-06-09
-------------------

:func:`~hypothesis.strategies.from_type` now handles numpy array types:
:obj:`np.typing.ArrayLike <numpy.typing.ArrayLike>`,
:obj:`np.typing.NDArray <numpy.typing.NDArray>`, and parameterized
versions including :class:`np.ndarray[shape, elem_type] <numpy.ndarray>`.

.. _v6.76.0:

-------------------
6.76.0 - 2023-06-04
-------------------

Warn in :func:`~hypothesis.strategies.from_type` if the inferred strategy
has no variation (always returning default instances). Also handles numpy
data types by calling :func:`~hypothesis.extra.numpy.from_dtype` on the
corresponding dtype, thus ensuring proper variation for these types.

.. _v6.75.9:

-------------------
6.75.9 - 2023-05-31
-------------------

:func:`~hypothesis.strategies.from_type` now works in cases where we use
:func:`~hypothesis.strategies.builds` to create an instance and the constructor
has an argument which would lead to recursion.  Previously, this would raise
an error if the argument had a default value.

Thanks to Joachim B Haga for reporting and fixing this problem.

.. _v6.75.8:

-------------------
6.75.8 - 2023-05-31
-------------------

In preparation for supporting JAX in :ref:`hypothesis.extra.array_api <array-api>`,
this release supports immutable arrays being generated via :func:`xps.arrays`.
In particular, we internally removed an instance of in-place array modification,
which isn't possible for an immutable array.

.. _v6.75.7:

-------------------
6.75.7 - 2023-05-30
-------------------

This release fixes some ``.patch``-file bugs from :ref:`version 6.75 <v6.75.0>`,
and adds automatic support for writing ``@hypothesis.example()`` or ``@example()``
depending on the current style in your test file - defaulting to the latter.

Note that this feature requires :pypi:`libcst` to be installed, and :pypi:`black`
is strongly recommended.  You can ensure you have the dependencies with
``pip install "hypothesis[cli,codemods]"``.

.. _v6.75.6:

-------------------
6.75.6 - 2023-05-27
-------------------

This patch continues the work started in :pull:`3651` by adding
:pypi:`ruff` linter rules for :pypi:`pyflakes`, :pypi:`flake8-comprehensions`,
and :pypi:`flake8-implicit-str-concat`.

.. _v6.75.5:

-------------------
6.75.5 - 2023-05-26
-------------------

This patch updates our linter stack to use :pypi:`ruff`, and fixes some
previously-ignored lints.  Thanks to Christian Clauss for his careful
review and :pull:`3651`!

.. _v6.75.4:

-------------------
6.75.4 - 2023-05-26
-------------------

Hypothesis will now record an event for more cases where data is marked
invalid, including for exceeding the internal depth limit.

.. _v6.75.3:

-------------------
6.75.3 - 2023-05-14
-------------------

This patch fixes :func:`~hypothesis.strategies.complex_numbers` accidentally
invalidating itself when passed magnitude arguments for 32 and 64-bit widths,
i.e. 16- and 32-bit floats, due to not internally down-casting numbers (:issue:`3573`).

.. _v6.75.2:

-------------------
6.75.2 - 2023-05-04
-------------------

Improved the documentation regarding how to use :class:`~hypothesis.database.GitHubArtifactDatabase`
and fixed a bug that occurred in repositories with no existing artifacts.

Thanks to Agustín Covarrubias for this contribution.

.. _v6.75.1:

-------------------
6.75.1 - 2023-04-30
-------------------

``hypothesis.errors`` will now raise :py:exc:`AttributeError` when attempting
to access an undefined attribute, rather than returning :py:obj:`None`.

.. _v6.75.0:

-------------------
6.75.0 - 2023-04-30
-------------------

Sick of adding :obj:`@example() <hypothesis.example>`\ s by hand?
Our Pytest plugin now writes ``.patch`` files to insert them for you, making
`this workflow <https://blog.nelhage.com/post/property-testing-like-afl/>`__
easier than ever before.

Note that you'll need :pypi:`LibCST <libcst>` (via :ref:`codemods`), and that
:obj:`@example().via() <hypothesis.example.via>` requires :pep:`614`
(Python 3.9 or later).

.. _v6.74.1:

-------------------
6.74.1 - 2023-04-28
-------------------

This patch provides better error messages for datetime- and timedelta-related
invalid dtypes in our Pandas extra (:issue:`3518`).
Thanks to Nick Muoh at the PyCon Sprints!

.. _v6.74.0:

-------------------
6.74.0 - 2023-04-26
-------------------

This release adds support for `nullable pandas dtypes <https://pandas.pydata.org/docs/user_guide/integer_na.html>`__
in :func:`~hypothesis.extra.pandas` (:issue:`3604`).
Thanks to Cheuk Ting Ho for implementing this at the PyCon sprints!

.. _v6.73.1:

-------------------
6.73.1 - 2023-04-27
-------------------

This patch updates our minimum Numpy version to 1.16, and restores compatibility
with versions before 1.20, which were broken by a mistake in Hypothesis 6.72.4
(:issue:`3625`).

.. _v6.73.0:

-------------------
6.73.0 - 2023-04-25
-------------------

This release upgrades the :ref:`explain phase <phases>` (:issue:`3411`).

* Following the first failure, Hypothesis will (:ref:`usually <phases>`) track which
  lines of code were executed by passing and failing examples, and report where they
  diverged - with some heuristics to drop unhelpful reports.  This is an existing
  feature, now upgraded and newly enabled by default.

* After shrinking to a minimal failing example, Hypothesis will try to find parts of
  the example -- e.g. separate args to :func:`@given() <hypothesis.given>` -- which
  can vary freely without changing the result of that minimal failing example.
  If the automated experiments run without finding a passing variation, we leave a
  comment in the final report:

  .. code-block:: python

      test_x_divided_by_y(
          x=0,  # or any other generated value
          y=0,
      )

Just remember that the *lack* of an explanation sometimes just means that Hypothesis
couldn't efficiently find one, not that no explanation (or simpler failing example)
exists.

.. _v6.72.4:

-------------------
6.72.4 - 2023-04-25
-------------------

This patch fixes type annotations for the :func:`~hypothesis.extra.numpy.arrays`
strategy.  Thanks to Francesc Elies for :pull:`3602`.

.. _v6.72.3:

-------------------
6.72.3 - 2023-04-25
-------------------

This patch fixes a bug with :func:`~hypothesis.strategies.from_type()` with ``dict[tuple[int, int], str]``
(:issue:`3527`).

    Thanks to Nick Muoh at the PyCon Sprints!

.. _v6.72.2:

-------------------
6.72.2 - 2023-04-24
-------------------

This patch refactors our internals to facilitate an upcoming feature.

.. _v6.72.1:

-------------------
6.72.1 - 2023-04-19
-------------------

This patch fixes some documentation and prepares for future features.

.. _v6.72.0:

-------------------
6.72.0 - 2023-04-16
-------------------

This release deprecates ``Healthcheck.all()``, and :ref:`adds a codemod <codemods>`
to automatically replace it with ``list(Healthcheck)`` (:issue:`3596`).

.. _v6.71.0:

-------------------
6.71.0 - 2023-04-07
-------------------

This release adds :class:`~hypothesis.database.GitHubArtifactDatabase`, a new database
backend that allows developers to access the examples found by a Github Actions CI job.
This is particularly useful for workflows that involve continuous fuzzing,
like `HypoFuzz <https://hypofuzz.com/>`__.

Thanks to Agustín Covarrubias for this feature!

.. _v6.70.2:

-------------------
6.70.2 - 2023-04-03
-------------------

This patch clarifies the reporting of time spent generating data. A
simple arithmetic mean of the percentage of time spent can be
misleading; reporting the actual time spent avoids misunderstandings.

Thanks to Andrea Reina for reporting and fixing :issue:`3598`!

.. _v6.70.1:

-------------------
6.70.1 - 2023-03-27
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.70.0:

-------------------
6.70.0 - 2023-03-16
-------------------

This release adds an optional ``domains=`` parameter to the
:func:`~hypothesis.strategies.emails` strategy, and excludes
the special-use :wikipedia:`.arpa` domain from the default
strategy (:issue:`3567`).

Thanks to Jens Tröger for reporting and fixing this bug!

.. _v6.69.0:

-------------------
6.69.0 - 2023-03-15
-------------------

This release turns ``HealthCheck.return_value`` and ``HealthCheck.not_a_test_method``
into unconditional errors.  Passing them to ``suppress_health_check=`` is therefore a deprecated no-op.
(:issue:`3568`).  Thanks to Reagan Lee for the patch!

Separately, GraalPy can now run and pass most of the hypothesis test suite (:issue:`3587`).

.. _v6.68.3:

-------------------
6.68.3 - 2023-03-15
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.68.2:

-------------------
6.68.2 - 2023-02-17
-------------------

This patch fixes missing imports of the :mod:`re` module, when :doc:`ghostwriting <ghostwriter>`
tests which include compiled patterns or regex flags.
Thanks to Jens Heinrich for reporting and promptly fixing this bug!

.. _v6.68.1:

-------------------
6.68.1 - 2023-02-12
-------------------

This patch adds some private hooks for use in research on
`Schemathesis <https://github.com/schemathesis/schemathesis>`__
(`see our preprint here <https://arxiv.org/abs/2112.10328>`__).

.. _v6.68.0:

-------------------
6.68.0 - 2023-02-09
-------------------

This release adds support for the Array API's `2022.12 release
<https://data-apis.org/array-api/2022.12/>`_ via the ``api_version`` argument in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`. Concretely this
involves complex support in its existing strategies, plus an introduced
:func:`xps.complex_dtypes` strategy.

Additionally this release now treats :ref:`hypothesis.extra.array_api
<array-api>` as stable, meaning breaking changes should only happen with major
releases of Hypothesis.

.. _v6.67.1:

-------------------
6.67.1 - 2023-02-05
-------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.67.0:

-------------------
6.67.0 - 2023-02-05
-------------------

This release allows for more precise generation of complex numbers using
:func:`~hypothesis.extra.numpy.from_dtype`, by supporting the ``width``,
``min_magnitude``, and ``min_magnitude`` arguments (:issue:`3468`).

Thanks to Felix Divo for this feature!

.. _v6.66.2:

-------------------
6.66.2 - 2023-02-04
-------------------

This patch fixes a rare ``RecursionError`` when pretty-printing a multi-line
object without type-specific printer, which was passed to a function which
returned the same object by ``.map()`` or :func:`~hypothesis.strategies.builds`
and thus recursed due to the new pretty reprs in Hypothesis :ref:`v6.65.0`
(:issue:`3560`).  Apologies to all those affected.

.. _v6.66.1:

-------------------
6.66.1 - 2023-02-03
-------------------

This makes :func:`~hypothesis.extra.numpy.from_dtype` pass through the parameter
``allow_subnormal`` for complex dtypes.

.. _v6.66.0:

-------------------
6.66.0 - 2023-02-02
-------------------

This release adds a ``width`` parameter to :func:`~hypothesis.strategies.complex_numbers`,
analogously to :func:`~hypothesis.strategies.floats`.

Thanks to Felix Divo for the new feature!

.. _v6.65.2:

-------------------
6.65.2 - 2023-01-27
-------------------

This patch fixes invalid annotations detected for the tests generated by
:doc:`Ghostwritter <ghostwriter>`. It will now correctly generate ``Optional``
types with just one type argument and handle union expressions inside of type
arguments correctly. Additionally, it now supports code with the
``from __future__ import annotations`` marker for Python 3.10 and newer.

.. _v6.65.1:

-------------------
6.65.1 - 2023-01-26
-------------------

This release improves the pretty-printing of enums in falsifying examples,
so that they print as their full identifier rather than their repr.

.. _v6.65.0:

-------------------
6.65.0 - 2023-01-24
-------------------

Hypothesis now reports some failing inputs by showing the call which constructed
an object, rather than the repr of the object.  This can be helpful when the default
repr does not include all relevant details, and will unlock further improvements
in a future version.

For now, we capture calls made via :func:`~hypothesis.strategies.builds`, and via
:ref:`SearchStrategy.map() <mapping>`.

.. _v6.64.0:

-------------------
6.64.0 - 2023-01-23
-------------------

The :doc:`Ghostwritter <ghostwriter>` will now include type annotations on tests
for type-annotated code.  If you want to force this to happen (or not happen),
pass a boolean to the new ``annotate=`` argument to the Python functions, or
the ``--[no-]annotate`` CLI flag.

Thanks to Nicolas Ganz for this new feature!

.. _v6.63.0:

-------------------
6.63.0 - 2023-01-20
-------------------

:func:`~hypothesis.extra.pandas.range_indexes` now accepts a ``name=`` argument,
to generate named :class:`pandas.RangeIndex` objects.

Thanks to Sam Watts for this new feature!

.. _v6.62.1:

-------------------
6.62.1 - 2023-01-14
-------------------

This patch tweaks :func:`xps.arrays` internals to improve PyTorch compatibility.
Specifically, ``torch.full()`` does not accept integers as the shape argument
(n.b. technically "size" in torch), but such behaviour is expected in internal
code, so we copy the ``torch`` module and patch in a working ``full()`` function.

.. _v6.62.0:

-------------------
6.62.0 - 2023-01-08
-------------------

A classic error when testing is to write a test function that can never fail,
even on inputs that aren't allowed or manually provided.  By analogy to the
design pattern of::

    @pytest.mark.parametrize("arg", [
        ...,  # passing examples
        pytest.param(..., marks=[pytest.mark.xfail])  # expected-failing input
    ])

we now support :obj:`@example(...).xfail() <hypothesis.example.xfail>`, with
the same (optional) ``condition``, ``reason``, and ``raises`` arguments as
``pytest.mark.xfail()``.

Naturally you can also write ``.via(...).xfail(...)``, or ``.xfail(...).via(...)``,
if you wish to note the provenance of expected-failing examples.

.. _v6.61.3:

-------------------
6.61.3 - 2023-01-08
-------------------

This patch teaches our enhanced :func:`~typing.get_type_hints` function to
'see through' :obj:`~functools.partial` application, allowing inference
from type hints to work in a few more cases which aren't (yet!) supported
by the standard-library version.

.. _v6.61.2:

-------------------
6.61.2 - 2023-01-07
-------------------

This patch improves our pretty-printing of failing examples, including
some refactoring to prepare for exciting future features.

.. _v6.61.1:

-------------------
6.61.1 - 2023-01-06
-------------------

This patch brings our :func:`~hypothesis.provisional.domains` and
:func:`~hypothesis.strategies.emails` strategies into compliance with
:rfc:`RFC 5890 §2.3.1 <5890>`: we no longer generate parts-of-domains
where the third and fourth characters are ``--`` ("R-LDH labels"),
though future versions *may* deliberately generate ``xn--`` punycode
labels.  Thanks to :pypi:`python-email-validator` for `the report
<https://github.com/JoshData/python-email-validator/issues/92>`__!

.. _v6.61.0:

-------------------
6.61.0 - 2022-12-11
-------------------

This release improves our treatment of database keys, which based on (among other things)
the source code of your test function.  We now post-process this source to ignore
decorators, comments, trailing whitespace, and blank lines - so that you can add
:obj:`@example() <hypothesis.example>`\ s or make some small no-op edits to your code
without preventing replay of any known failing or covering examples.

.. _v6.60.1:

-------------------
6.60.1 - 2022-12-11
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.60.0:

-------------------
6.60.0 - 2022-12-04
-------------------

This release improves Hypothesis' ability to resolve forward references in
type annotations. It fixes a bug that prevented
:func:`~hypothesis.strategies.builds` from being used with `pydantic models that
possess updated forward references <https://pydantic-docs.helpmanual.io/usage/postponed_annotations/>`__. See :issue:`3519`.

.. _v6.59.0:

-------------------
6.59.0 - 2022-12-02
-------------------

The :obj:`@example(...) <hypothesis.example>` decorator now has a ``.via()``
method, which future tools will use to track automatically-added covering
examples (:issue:`3506`).

.. _v6.58.2:

-------------------
6.58.2 - 2022-11-30
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.58.1:

-------------------
6.58.1 - 2022-11-26
-------------------

This patch shifts ``hypothesis[lark]`` from depending on the old :pypi:`lark-parser`
package to the new :pypi:`lark` package.  There are no code changes in Hypothesis,
it's just that Lark got a new name on PyPI for version 1.0 onwards.

.. _v6.58.0:

-------------------
6.58.0 - 2022-11-19
-------------------

:func:`~hypothesis.register_random` has used :mod:`weakref` since :ref:`v6.27.1`,
allowing the :class:`~random.Random`-compatible objects to be garbage-collected when
there are no other references remaining in order to avoid memory leaks.
We now raise an error or emit a warning when this seems likely to happen immediately.

The type annotation of :func:`~hypothesis.register_random` was also widened so that
structural subtypes of :class:`~random.Random` are accepted by static typecheckers.

.. _v6.57.1:

-------------------
6.57.1 - 2022-11-14
-------------------

This patch updates some internal type annotations and fixes a formatting bug in the
:obj:`~hypothesis.Phase.explain` phase reporting.

.. _v6.57.0:

-------------------
6.57.0 - 2022-11-14
-------------------

Hypothesis now raises an error if you passed a strategy as the ``alphabet=``
argument to :func:`~hypothesis.strategies.text`, and it generated something
which was not a length-one string.  This has never been supported, we're just
adding explicit validation to catch cases like `this StackOverflow question
<https://stackoverflow.com/a/74336909/9297601>`__.

.. _v6.56.4:

-------------------
6.56.4 - 2022-10-28
-------------------

This patch updates some docs, and depends on :pypi:`exceptiongroup` 1.0.0
final to avoid a bug in the previous version.

.. _v6.56.3:

-------------------
6.56.3 - 2022-10-17
-------------------

This patch teaches :func:`~hypothesis.strategies.text` to rewrite a few more
filter predicates (:issue:`3134`).  You're unlikely to notice any change.

.. _v6.56.2:

-------------------
6.56.2 - 2022-10-10
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy, and fixes some
incorrect examples in the docs for :func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes`.

.. _v6.56.1:

-------------------
6.56.1 - 2022-10-05
-------------------

This patch improves the error message when Hypothesis detects "flush to zero"
mode for floating-point: we now report which package(s) enabled this, which
can make debugging much easier.  See :issue:`3458` for details.

.. _v6.56.0:

-------------------
6.56.0 - 2022-10-02
-------------------

This release defines ``__bool__()`` on :class:`~hypothesis.strategies.SearchStrategy`.
It always returns ``True``, like before, but also emits a warning to help with
cases where you intended to draw a value (:issue:`3463`).

.. _v6.55.0:

-------------------
6.55.0 - 2022-09-29
-------------------

In preparation for `future versions of the Array API standard
<https://data-apis.org/array-api/latest/future_API_evolution.html>`__,
:func:`~hypothesis.extra.array_api.make_strategies_namespace` now accepts an
optional ``api_version`` argument, which determines the version conformed to by
the returned strategies namespace. If ``None``, the version of the passed array
module ``xp`` is inferred.

This release also introduces :func:`xps.real_dtypes`. This is currently
equivalent to the existing :func:`xps.numeric_dtypes` strategy, but exists
because the latter is expected to include complex numbers in the next version of
the standard.

.. _v6.54.6:

-------------------
6.54.6 - 2022-09-18
-------------------

If multiple explicit examples (from :obj:`@example() <hypothesis.example>`)
raise a Skip exception, for consistency with generated examples we now re-raise
the first instead of collecting them into an ExceptionGroup (:issue:`3453`).

.. _v6.54.5:

-------------------
6.54.5 - 2022-09-05
-------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.54.4:

-------------------
6.54.4 - 2022-08-20
-------------------

This patch fixes some type annotations for Python 3.9 and earlier (:issue:`3397`),
and teaches :ref:`explain mode <phases>` about certain locations it should not
bother reporting (:issue:`3439`).

.. _v6.54.3:

-------------------
6.54.3 - 2022-08-12
-------------------

This patch teaches the Ghostwriter an additional check for function
and class locations that should make it use public APIs more often.

.. _v6.54.2:

-------------------
6.54.2 - 2022-08-10
-------------------

This patch fixes our workaround for `a pytest bug where the inner exceptions in
an ExceptionGroup are not displayed <https://github.com/pytest-dev/pytest/issues/9159>`__
(:issue:`3430`).

.. _v6.54.1:

-------------------
6.54.1 - 2022-08-02
-------------------

This patch makes ``FailedHealthCheck`` and ``DeadlineExceeded`` exceptions
picklable, for compatibility with Django's parallel test runner (:issue:`3426`).

.. _v6.54.0:

-------------------
6.54.0 - 2022-08-02
-------------------

Reporting of :obj:`multiple failing examples <hypothesis.settings.report_multiple_bugs>`
now uses the :pep:`654` `ExceptionGroup <https://docs.python.org/3.11/library/exceptions.html#ExceptionGroup>`__ type, which is provided by the
:pypi:`exceptiongroup` backport on Python 3.10 and earlier (:issue:`3175`).
``hypothesis.errors.MultipleFailures`` is therefore deprecated.

Failing examples and other reports are now stored as :pep:`678` exception notes, which
ensures that they will always appear together with the traceback and other information
about their respective error.

.. _v6.53.0:

-------------------
6.53.0 - 2022-07-25
-------------------

:func:`~hypothesis.extra.django.from_field` now supports ``UsernameField``
from :mod:`django.contrib.auth.forms`.

Thanks to Afonso Silva for reporting and working on :issue:`3417`.

.. _v6.52.4:

-------------------
6.52.4 - 2022-07-22
-------------------

This patch improves the error message when you pass filenames to the :command:`hypothesis write`
CLI, which takes the name of a module or function (e.g. :command:`hypothesis write gzip` or
:command:`hypothesis write package.some_function` rather than :command:`hypothesis write script.py`).

Thanks to Ed Rogers for implementing this as part of the SciPy 2022 sprints!

.. _v6.52.3:

-------------------
6.52.3 - 2022-07-19
-------------------

This patch ensures that the warning for non-interactive ``.example()``
points to your code instead of Hypothesis internals (:issue:`3403`).

Thanks to @jameslamb for this fix.

.. _v6.52.2:

-------------------
6.52.2 - 2022-07-19
-------------------

This patch makes :func:`~hypothesis.strategies.integers` more likely to
generate boundary values for large two-sided intervals (:issue:`2942`).

.. _v6.52.1:

-------------------
6.52.1 - 2022-07-18
-------------------

This patch adds filter rewriting for :func:`math.isfinite`, :func:`math.isinf`, and :func:`math.isnan`
on :func:`~hypothesis.strategies.integers` or :func:`~hypothesis.strategies.floats` (:issue:`2701`).

Thanks to Sam Clamons at the SciPy Sprints!

.. _v6.52.0:

-------------------
6.52.0 - 2022-07-18
-------------------

This release adds the ``allow_subnormal`` argument to :func:`~hypothesis.strategies.complex_numbers` by
applying it to each of the real and imaginary parts separately. Closes :issue:`3390`.

Thanks to Evan Tey for this fix.

.. _v6.51.0:

-------------------
6.51.0 - 2022-07-17
-------------------

Issue a deprecation warning if a function decorated with
:func:`@composite <hypothesis.strategies.composite>`
does not draw any values (:issue:`3384`).

Thanks to Grzegorz Zieba, Rodrigo Girão, and Thomas Ball for
working on this at the EuroPython sprints!

.. _v6.50.1:

-------------------
6.50.1 - 2022-07-09
-------------------

This patch improves the error messages in :obj:`@example() <hypothesis.example>`
argument validation following the recent release of :ref:`6.49.1 <v6.49.1>`.

.. _v6.50.0:

-------------------
6.50.0 - 2022-07-09
-------------------

This release allows :func:`~hypothesis.extra.numpy.from_dtype` to generate
Unicode strings which cannot be encoded in UTF-8, but are valid in Numpy
arrays (which use UTF-32).

This logic will only be used with :pypi:`numpy` >= 1.19, because earlier
versions have `an issue <https://github.com/numpy/numpy/issues/15363>`__
which led us to revert :ref:`Hypothesis 5.2 <v5.2.0>` last time!

.. _v6.49.1:

-------------------
6.49.1 - 2022-07-05
-------------------

This patch fixes some inconsistency between argument handling for
:obj:`@example <hypothesis.example>` and :func:`@given <hypothesis.given>`
(:issue:`2706 <2706#issuecomment-1168363177>`).

.. _v6.49.0:

-------------------
6.49.0 - 2022-07-04
-------------------

This release uses :pep:`612` :obj:`python:typing.ParamSpec` (or the
:pypi:`typing-extensions` backport) to express the first-argument-removing
behaviour of :func:`@st.composite <hypothesis.strategies.composite>`
and signature-preservation of :func:`~hypothesis.strategies.functions`
to IDEs, editor plugins, and static type checkers such as :pypi:`mypy`.

.. _v6.48.3:

-------------------
6.48.3 - 2022-07-03
-------------------

:func:`hypothesis.event` now works for hashable objects which do not
support weakrefs, such as integers and tuples.

.. _v6.48.2:

-------------------
6.48.2 - 2022-06-29
-------------------

This patch tidies up some internal introspection logic, which will improve
support for positional-only arguments in a future release (:issue:`2706`).

.. _v6.48.1:

-------------------
6.48.1 - 2022-06-27
-------------------

This release automatically rewrites some simple filters, such as
``floats().filter(lambda x: x >= 10)`` to the more efficient
``floats(min_value=10)``, based on the AST of the predicate.

We continue to recommend using the efficient form directly wherever
possible, but this should be useful for e.g. :pypi:`pandera` "``Checks``"
where you already have a simple predicate and translating manually
is really annoying.  See :issue:`2701` for details.

.. _v6.48.0:

-------------------
6.48.0 - 2022-06-27
-------------------

This release raises :class:`~unittest.SkipTest` for tests which never executed any
examples, for example because the :obj:`~hypothesis.settings.phases` setting
excluded the :obj:`~hypothesis.Phase.explicit`, :obj:`~hypothesis.Phase.reuse`,
and :obj:`~hypothesis.Phase.generate` phases.  This helps to avoid cases where
broken tests appear to pass, because they didn't actually execute (:issue:`3328`).

.. _v6.47.5:

-------------------
6.47.5 - 2022-06-25
-------------------

This patch fixes type annotations that had caused the signature of
:func:`@given <hypothesis.given>` to be partially-unknown to type-checkers for Python
versions before 3.10.

.. _v6.47.4:

-------------------
6.47.4 - 2022-06-23
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` on Python 3.11,
following `python/cpython#93754 <https://github.com/python/cpython/pull/93754/>`__.

.. _v6.47.3:

-------------------
6.47.3 - 2022-06-15
-------------------

This patch makes the :obj:`~hypothesis.HealthCheck.too_slow` health check more
consistent with long :obj:`~hypothesis.settings.deadline` tests (:issue:`3367`)
and fixes an install issue under :pypi:`pipenv` which was introduced in
:ref:`Hypothesis 6.47.2 <v6.47.2>` (:issue:`3374`).

.. _v6.47.2:

-------------------
6.47.2 - 2022-06-12
-------------------

We now use the :pep:`654` `ExceptionGroup <https://docs.python.org/3.11/library/exceptions.html#ExceptionGroup>`__
type - provided by the :pypi:`exceptiongroup` backport on older Pythons -
to ensure that if multiple errors are raised in teardown, they will all propagate.

.. _v6.47.1:

-------------------
6.47.1 - 2022-06-10
-------------------

Our pretty-printer no longer sorts dictionary keys, since iteration order is
stable in Python 3.7+ and this can affect reproducing examples (:issue:`3370`).
This PR was kindly supported by `Ordina Pythoneers
<https://www.ordina.nl/vakgebieden/python/>`__.

.. _v6.47.0:

-------------------
6.47.0 - 2022-06-07
-------------------

The :doc:`Ghostwritter <ghostwriter>` can now write tests for
:obj:`@classmethod <classmethod>` or :obj:`@staticmethod <staticmethod>`
methods, in addition to the existing support for functions and other callables
(:issue:`3318`).  Thanks to Cheuk Ting Ho for the patch.

.. _v6.46.11:

--------------------
6.46.11 - 2022-06-02
--------------------

Mention :func:`hypothesis.strategies.timezones`
in the documentation of :func:`hypothesis.strategies.datetimes` for completeness.

Thanks to George Macon for this addition.

.. _v6.46.10:

--------------------
6.46.10 - 2022-06-01
--------------------

This release contains some small improvements to our documentation.
Thanks to Felix Divo for his contribution!

.. _v6.46.9:

-------------------
6.46.9 - 2022-05-25
-------------------

This patch by Adrian Garcia Badaracco adds type annotations
to some private internals (:issue:`3074`).

.. _v6.46.8:

-------------------
6.46.8 - 2022-05-25
-------------------

This patch by Phillip Schanely makes changes to the
:func:`~hypothesis.strategies.floats` strategy when ``min_value`` or ``max_value`` is
present.
Hypothesis will now be capable of generating every representable value in the bounds.
You may notice that hypothesis is more likely to test values near boundaries, and values
that are very close to zero.

These changes also support future integrations with symbolic execution tools and fuzzers
(:issue:`3086`).

.. _v6.46.7:

-------------------
6.46.7 - 2022-05-19
-------------------

This patch updates the type annotations for :func:`~hypothesis.strategies.tuples` and
:func:`~hypothesis.strategies.one_of` so that type-checkers require its arguments to be
positional-only, and so that it no longer fails under pyright-strict mode (see
:issue:`3348`). Additional changes are made to Hypothesis' internals improve pyright
scans.

.. _v6.46.6:

-------------------
6.46.6 - 2022-05-18
-------------------

This patch by Cheuk Ting Ho adds support for :pep:`655` ``Required`` and ``NotRequired`` as attributes of
:class:`~python:typing.TypedDict` in :func:`~hypothesis.strategies.from_type` (:issue:`3339`).

.. _v6.46.5:

-------------------
6.46.5 - 2022-05-15
-------------------

This patch fixes :func:`~hypothesis.extra.numpy.from_dtype` with long-precision
floating-point datatypes (typecode ``g``; see :func:`numpy:numpy.typename`).

.. _v6.46.4:

-------------------
6.46.4 - 2022-05-15
-------------------

This patch improves some error messages for custom signatures
containing invalid parameter names (:issue:`3317`).

.. _v6.46.3:

-------------------
6.46.3 - 2022-05-11
-------------------

This patch by Cheuk Ting Ho makes it an explicit error to call :func:`~hypothesis.strategies.from_type`
or :func:`~hypothesis.strategies.register_type_strategy` with types that have no runtime instances (:issue:`3280`).

.. _v6.46.2:

-------------------
6.46.2 - 2022-05-03
-------------------

This patch fixes silently dropping examples when the :obj:`@example <hypothesis.example>`
decorator is applied to itself (:issue:`3319`).  This was always a weird pattern, but now it
works.  Thanks to Ray Sogata, Keeri Tramm, and Kevin Khuong for working on this patch!

.. _v6.46.1:

-------------------
6.46.1 - 2022-05-01
-------------------

This patch fixes a rare bug where we could incorrectly treat
:obj:`~python:inspect.Parameter.empty` as a type annotation,
if the callable had an explicitly assigned ``__signature__``.

.. _v6.46.0:

-------------------
6.46.0 - 2022-05-01
-------------------

This release adds an ``allow_nil`` argument to :func:`~hypothesis.strategies.uuids`,
which you can use to... generate the nil UUID.  Thanks to Shlok Gandhi for the patch!

.. _v6.45.4:

-------------------
6.45.4 - 2022-05-01
-------------------

This patch fixes some missing imports for certain :doc:`Ghostwritten <ghostwriter>`
tests.  Thanks to Mel Seto for fixing :issue:`3316`.

.. _v6.45.3:

-------------------
6.45.3 - 2022-04-30
-------------------

This patch teaches :doc:`the Ghostwriter <ghostwriter>` to recognize
many more common argument names (:issue:`3311`).

.. _v6.45.2:

-------------------
6.45.2 - 2022-04-29
-------------------

This patch fixes :issue:`3314`, where Hypothesis would raise an internal
error from :func:`~hypothesis.provisional.domains` or (only on Windows)
from :func:`~hypothesis.strategies.timezones` in some rare circumstances
where the installation was subtly broken.

Thanks to Munir Abdinur for this contribution.

.. _v6.45.1:

-------------------
6.45.1 - 2022-04-27
-------------------

This release fixes deprecation warnings about ``sre_compile`` and ``sre_parse``
imports and ``importlib.resources`` usage when running Hypothesis on Python 3.11.

Thanks to Florian Bruhin for this contribution.

.. _v6.45.0:

-------------------
6.45.0 - 2022-04-22
-------------------

This release updates :func:`xps.indices` by introducing an ``allow_newaxis``
argument, defaulting to ``False``. If ``allow_newaxis=True``, indices can be
generated that add dimensions to arrays, which is achieved by the indexer
containing ``None``. This change is to support a specification change that
expand dimensions via indexing (`data-apis/array-api#408
<https://github.com/data-apis/array-api/pull/408>`_).

.. _v6.44.0:

-------------------
6.44.0 - 2022-04-21
-------------------

This release adds a ``names`` argument to :func:`~hypothesis.extra.pandas.indexes`
and :func:`~hypothesis.extra.pandas.series`, so that you can create Pandas
objects with specific or varied names.

Contributed by Sam Watts.

.. _v6.43.3:

-------------------
6.43.3 - 2022-04-18
-------------------

This patch updates the type annotations for :func:`@given <hypothesis.given>`
so that type-checkers will warn on mixed positional and keyword arguments,
as well as fixing :issue:`3296`.

.. _v6.43.2:

-------------------
6.43.2 - 2022-04-16
-------------------

Fixed a type annotation for ``pyright --strict`` (:issue:`3287`).

.. _v6.43.1:

-------------------
6.43.1 - 2022-04-13
-------------------

This patch makes it an explicit error to call
:func:`~hypothesis.strategies.register_type_strategy` with a
`Pydantic GenericModel <https://docs.pydantic.dev/latest/concepts/models/#generic-models>`__
and a callable, because ``GenericModel`` isn't actually a generic type at
runtime and so you have to register each of the "parametrized versions"
(actually subclasses!) manually.  See :issue:`2940` for more details.

.. _v6.43.0:

-------------------
6.43.0 - 2022-04-12
-------------------

This release makes it an explicit error to apply
:func:`@pytest.fixture <pytest:pytest.fixture>` to a function which has
already been decorated with :func:`@given() <hypothesis.given>`.  Previously,
``pytest`` would convert your test to a fixture, and then never run it.

.. _v6.42.3:

-------------------
6.42.3 - 2022-04-10
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` on a :class:`~python:typing.TypedDict`
with complex annotations, defined in a file using ``from __future__ import annotations``.
Thanks to Katelyn Gigante for identifying and fixing this bug!

.. _v6.42.2:

-------------------
6.42.2 - 2022-04-10
-------------------

The Hypothesis pytest plugin was not outputting valid xunit2 nodes when
``--junit-xml`` was specified. This has been broken since Pytest 5.4, which
changed the internal API for adding nodes to the junit report.

This also fixes the issue when using hypothesis with ``--junit-xml`` and
``pytest-xdist`` where the junit xml report would not be xunit2 compatible.
Now, when using with ``pytest-xdist``, the junit report will just omit the
``<properties>`` node.

For more details, see `this pytest issue <https://github.com/pytest-dev/pytest/issues/1126#issuecomment-484581283>`__,
`this pytest issue <https://github.com/pytest-dev/pytest/issues/7767#issuecomment-1082436256>`__,
and :issue:`1935`

Thanks to Brandon Chinn for this bug fix!

.. _v6.42.1:

-------------------
6.42.1 - 2022-04-10
-------------------

This patch fixes pretty-printing of regular expressions in Python 3.11.0a7, and
updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,.

.. _v6.42.0:

-------------------
6.42.0 - 2022-04-09
-------------------

This release makes ``st.functions(pure=True)`` less noisy (:issue:`3253`),
and generally improves pretty-printing of functions.

.. _v6.41.0:

-------------------
6.41.0 - 2022-04-01
-------------------

This release changes the implementation of :const:`~hypothesis.infer` to be an alias
for :obj:`python:Ellipsis`. E.g. ``@given(a=infer)`` is now equivalent to ``@given(a=...)``. Furthermore, ``@given(...)`` can now be specified so that
:func:`@given <hypothesis.given>` will infer the strategies for *all* arguments of the
decorated function based on its annotations.

.. _v6.40.3:

-------------------
6.40.3 - 2022-04-01
-------------------

This patch simplifies the repr of the strategies namespace returned in
:func:`~hypothesis.extra.array_api.make_strategies_namespace`, e.g.

.. code-block:: pycon

    >>> from hypothesis.extra.array_api import make_strategies_namespace
    >>> from numpy import array_api as xp
    >>> xps = make_strategies_namespace(xp)
    >>> xps
    make_strategies_namespace(numpy.array_api)

.. _v6.40.2:

-------------------
6.40.2 - 2022-04-01
-------------------

Fixed :func:`~hypothesis.strategies.from_type` support for
:pep:`604` union types, like ``int | None`` (:issue:`3255`).

.. _v6.40.1:

-------------------
6.40.1 - 2022-04-01
-------------------

Fixed an internal error when ``given()`` was passed a lambda.

.. _v6.40.0:

-------------------
6.40.0 - 2022-03-29
-------------------

:doc:`The Ghostwriter <ghostwriter>` can now write tests which check that
two or more functions are equivalent on valid inputs, *or* raise the same
type of exception for invalid inputs (:issue:`3267`).

.. _v6.39.6:

-------------------
6.39.6 - 2022-03-27
-------------------

This patch makes some quality-of-life improvements to the
:doc:`Ghostwriter <ghostwriter>`: we guess the :func:`~hypothesis.strategies.text`
strategy for arguments named ``text`` (...obvious in hindsight, eh?);
and improved the error message if you accidentally left in a
:func:`~hypothesis.strategies.nothing` or broke your :pypi:`rich` install.

.. _v6.39.5:

-------------------
6.39.5 - 2022-03-26
-------------------

This patch improves our error detection and message when Hypothesis is run
on a Python implementation without support for ``-0.0``, which is required
for the :func:`~hypothesis.strategies.floats` strategy but can be disabled by
`unsafe compiler options <https://simonbyrne.github.io/notes/fastmath/>`__
(:issue:`3265`).

.. _v6.39.4:

-------------------
6.39.4 - 2022-03-17
-------------------

This patch tweaks some internal formatting.  There is no user-visible change.

.. _v6.39.3:

-------------------
6.39.3 - 2022-03-07
-------------------

If the :obj:`~hypothesis.Phase.shrink` phase is disabled, we now stop the
:obj:`~hypothesis.Phase.generate` phase as soon as an error is found regardless
of the value of the ``report_multiple_examples`` setting, since that's
probably what you wanted (:issue:`3244`).

.. _v6.39.2:

-------------------
6.39.2 - 2022-03-07
-------------------

This patch clarifies rare error messages in
:func:`~hypothesis.strategies.builds` (:issue:`3225`) and
:func:`~hypothesis.strategies.floats` (:issue:`3207`).

.. _v6.39.1:

-------------------
6.39.1 - 2022-03-03
-------------------

This patch fixes a regression where the bound inner function
(``your_test.hypothesis.inner_test``) would be invoked with positional
arguments rather than passing them by name, which broke
:pypi:`pytest-asyncio` (:issue:`3245`).

.. _v6.39.0:

-------------------
6.39.0 - 2022-03-01
-------------------

This release improves Hypothesis' handling of positional-only arguments,
which are now allowed :func:`@st.composite <hypothesis.strategies.composite>`
strategies.

On Python 3.8 and later, the first arguments to :func:`~hypothesis.strategies.builds`
and :func:`~hypothesis.extra.django.from_model` are now natively positional-only.
In cases which were already errors, the ``TypeError`` from incorrect usage will
therefore be raises immediately when the function is called, rather than when
the strategy object is used.

.. _v6.38.0:

-------------------
6.38.0 - 2022-02-26
-------------------

This release makes :func:`~hypothesis.strategies.floats` error *consistently* when
your floating-point hardware has been configured to violate IEEE-754 for
:wikipedia:`subnormal numbers <Subnormal_number>`, instead of
only when an internal assertion was tripped (:issue:`3092`).

If this happens to you, passing ``allow_subnormal=False`` will suppress the explicit
error.  However, we strongly recommend fixing the root cause by disabling global-effect
unsafe-math compiler options instead, or at least consulting e.g. Simon Byrne's
`Beware of fast-math <https://simonbyrne.github.io/notes/fastmath/>`__ explainer first.

.. _v6.37.2:

-------------------
6.37.2 - 2022-02-21
-------------------

This patch fixes a bug in stateful testing, where returning a single value
wrapped in :func:`~hypothesis.stateful.multiple` would be printed such that
the assigned variable was a tuple rather than the single element
(:issue:`3236`).

.. _v6.37.1:

-------------------
6.37.1 - 2022-02-21
-------------------

This patch fixes a warning under :pypi:`pytest` 7 relating to our
rich traceback display logic (:issue:`3223`).

.. _v6.37.0:

-------------------
6.37.0 - 2022-02-18
-------------------

When distinguishing multiple errors, Hypothesis now looks at the inner
exceptions of :pep:`654` ``ExceptionGroup``\ s.

.. _v6.36.2:

-------------------
6.36.2 - 2022-02-13
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.36.1:

-------------------
6.36.1 - 2022-01-31
-------------------

This patch fixes some deprecation warnings from :pypi:`pytest` 7.0,
along with some code formatting and docs updates.

.. _v6.36.0:

-------------------
6.36.0 - 2022-01-19
-------------------

This release disallows using :obj:`python:typing.Final`
with :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.strategies.register_type_strategy`.

Why?
Because ``Final`` can only be used during ``class`` definition.
We don't generate class attributes.

It also does not make sense as a runtime type on its own.

.. _v6.35.1:

-------------------
6.35.1 - 2022-01-17
-------------------

This patch fixes ``hypothesis write`` output highlighting with :pypi:`rich`
version 12.0 and later.

.. _v6.35.0:

-------------------
6.35.0 - 2022-01-08
-------------------

This release disallows using :obj:`python:typing.ClassVar`
with :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.strategies.register_type_strategy`.

Why?
Because ``ClassVar`` can only be used during ``class`` definition.
We don't generate class attributes.

It also does not make sense as a runtime type on its own.

.. _v6.34.2:

-------------------
6.34.2 - 2022-01-05
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.34.1:

-------------------
6.34.1 - 2021-12-31
-------------------

This patch fixes :issue:`3169`, an extremely rare bug which would
trigger if an internal least-recently-reused cache dropped a newly
added entry immediately after it was added.

.. _v6.34.0:

-------------------
6.34.0 - 2021-12-31
-------------------

This release fixes :issue:`3133` and :issue:`3144`, where attempting
to generate Pandas series of lists or sets would fail with confusing
errors if you did not specify ``dtype=object``.

.. _v6.33.0:

-------------------
6.33.0 - 2021-12-30
-------------------

This release disallows using :obj:`python:typing.TypeAlias`
with :func:`~hypothesis.strategies.from_type`
and :func:`~hypothesis.strategies.register_type_strategy`.

Why? Because ``TypeAlias`` is not really a type,
it is a tag for type checkers that some expression is a type alias,
not something else.

It does not make sense for Hypothesis to resolve it as a strategy.
References :issue:`2978`.

.. _v6.32.1:

-------------------
6.32.1 - 2021-12-23
-------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.32.0:

-------------------
6.32.0 - 2021-12-23
-------------------

This release drops support for Python 3.6, which `reached end of life upstream
<https://devguide.python.org/#status-of-python-branches>`__ on 2021-12-23.

.. _v6.31.6:

-------------------
6.31.6 - 2021-12-15
-------------------

This patch adds a temporary hook for a downstream tool,
which is not part of the public API.

.. _v6.31.5:

-------------------
6.31.5 - 2021-12-14
-------------------

This release updates our copyright headers to `use a general authorship statement and omit the year
<https://www.linuxfoundation.org/blog/copyright-notices-in-open-source-software-projects/>`__.

.. _v6.31.4:

-------------------
6.31.4 - 2021-12-11
-------------------

This patch makes the ``.example()`` method more representative of
test-time data generation, albeit often at a substantial cost to
readability (:issue:`3182`).

.. _v6.31.3:

-------------------
6.31.3 - 2021-12-10
-------------------

This patch improves annotations on some of Hypothesis' internal functions, in order to
deobfuscate the signatures of some strategies. In particular, strategies shared between
:ref:`hypothesis.extra.numpy <hypothesis-numpy>` and
:ref:`the hypothesis.extra.array_api extra <array-api>` will benefit from this patch.

.. _v6.31.2:

-------------------
6.31.2 - 2021-12-10
-------------------

This patch fix invariants display in stateful falsifying examples (:issue:`3185`).

.. _v6.31.1:

-------------------
6.31.1 - 2021-12-10
-------------------

This patch updates :func:`xps.indices` so no flat indices are generated, i.e.
generated indices will now always explicitly cover each axes of an array if no
ellipsis is present. This is to be consistent with a specification change that
dropped support for flat indexing
(`#272 <https://github.com/data-apis/array-api/pull/272>`_).

.. _v6.31.0:

-------------------
6.31.0 - 2021-12-09
-------------------

This release makes us compatible with :pypi:`Django` 4.0, in particular by adding
support for use of :mod:`zoneinfo` timezones (though we respect the new
``USE_DEPRECATED_PYTZ`` setting if you need it).

.. _v6.30.1:

-------------------
6.30.1 - 2021-12-05
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.30.0:

-------------------
6.30.0 - 2021-12-03
-------------------

This release adds an ``allow_subnormal`` argument to the
:func:`~hypothesis.strategies.floats` strategy, which can explicitly toggle the
generation of :wikipedia:`subnormal floats <Subnormal_number>` (:issue:`3155`).
Disabling such generation is useful when testing flush-to-zero builds of
libraries.

:func:`nps.from_dtype() <hypothesis.extra.numpy.from_dtype>` and
:func:`xps.from_dtype` can also accept the ``allow_subnormal`` argument, and
:func:`xps.from_dtype` or :func:`xps.arrays` will disable subnormals by default
if the array module ``xp`` is detected to flush-to-zero (like is typical with
CuPy).

.. _v6.29.3:

-------------------
6.29.3 - 2021-12-02
-------------------

This patch fixes a bug in :func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes`,
which restricted the patterns of singleton dimensions that could be generated for
dimensions that extended beyond ``base_shape`` (:issue:`3170`).

.. _v6.29.2:

-------------------
6.29.2 - 2021-12-02
-------------------

This patch clarifies our pretty-printing of DataFrames (:issue:`3114`).

.. _v6.29.1:

-------------------
6.29.1 - 2021-12-02
-------------------

This patch documents :func:`~hypothesis.strategies.timezones`
`Windows-only requirement <https://docs.python.org/3/library/zoneinfo.html#data-sources>`__
for the :pypi:`tzdata` package, and ensures that
``pip install hypothesis[zoneinfo]`` will install the latest version.

.. _v6.29.0:

-------------------
6.29.0 - 2021-11-29
-------------------

This release teaches :func:`~hypothesis.strategies.builds` to use
:func:`~hypothesis.strategies.deferred` when resolving unrecognised type hints,
so that you can conveniently register strategies for recursive types
with constraints on some arguments (:issue:`3026`):

.. code-block:: python

    class RecursiveClass:
        def __init__(self, value: int, next_node: typing.Optional["SomeClass"]):
            assert value > 0
            self.value = value
            self.next_node = next_node


    st.register_type_strategy(
        RecursiveClass, st.builds(RecursiveClass, value=st.integers(min_value=1))
    )

.. _v6.28.1:

-------------------
6.28.1 - 2021-11-28
-------------------

This release fixes some internal calculations related to collection sizes (:issue:`3143`).

.. _v6.28.0:

-------------------
6.28.0 - 2021-11-28
-------------------

This release modifies our :pypi:`pytest` plugin, to avoid importing Hypothesis
and therefore triggering :ref:`Hypothesis' entry points <entry-points>` for
test suites where Hypothesis is installed but not actually used (:issue:`3140`).

.. _v6.27.3:

-------------------
6.27.3 - 2021-11-28
-------------------

This release fixes :issue:`3080`, where :func:`~hypothesis.strategies.from_type`
failed on unions containing :pep:`585` builtin generic types (like ``list[int]``)
in Python 3.9 and later.

.. _v6.27.2:

-------------------
6.27.2 - 2021-11-26
-------------------

This patch makes the :command:`hypothesis codemod`
:ref:`command <hypothesis-cli>` somewhat faster.

.. _v6.27.1:

-------------------
6.27.1 - 2021-11-22
-------------------

This patch changes the backing datastructures of :func:`~hypothesis.register_random`
and a few internal caches to use :class:`weakref.WeakValueDictionary`.  This reduces
memory usage and may improve performance when registered :class:`~random.Random`
instances are only used for a subset of your tests (:issue:`3131`).

.. _v6.27.0:

-------------------
6.27.0 - 2021-11-22
-------------------

This release teaches Hypothesis' multiple-error reporting to format tracebacks
using :pypi:`pytest` or :pypi:`better-exceptions`, if they are installed and
enabled (:issue:`3116`).

.. _v6.26.0:

-------------------
6.26.0 - 2021-11-21
-------------------

Did you know that of the 2\ :superscript:`64` possible floating-point numbers,
2\ :superscript:`53` of them are ``nan`` - and Python prints them all the same way?

While nans *usually* have all zeros in the sign bit and mantissa, this
`isn't always true <https://wingolog.org/archives/2011/05/18/value-representation-in-javascript-implementations>`__,
and :wikipedia:`'signaling' nans might trap or error <NaN#Signaling_NaN>`.
To help distinguish such errors in e.g. CI logs, Hypothesis now prints ``-nan`` for
negative nans, and adds a comment like ``# Saw 3 signaling NaNs`` if applicable.

.. _v6.25.0:

-------------------
6.25.0 - 2021-11-19
-------------------

This release adds special filtering logic to make a few special cases
like ``s.map(lambda x: x)`` and ``lists().filter(len)`` more efficient
(:issue:`2701`).

.. _v6.24.6:

-------------------
6.24.6 - 2021-11-18
-------------------

This patch makes :func:`~hypothesis.strategies.floats` generate
:wikipedia:`"subnormal" floating point numbers <Subnormal_number>`
more often, as these rare values can have strange interactions with
`unsafe compiler optimisations like -ffast-math
<https://simonbyrne.github.io/notes/fastmath/#flushing_subnormals_to_zero>`__
(:issue:`2976`).

.. _v6.24.5:

-------------------
6.24.5 - 2021-11-16
-------------------

This patch fixes a rare internal error in the :func:`~hypothesis.strategies.datetimes`
strategy, where the implementation of ``allow_imaginary=False`` crashed when checking
a time during the skipped hour of a DST transition *if* the DST offset is negative -
only true of ``Europe/Dublin``, who we presume have their reasons - and the ``tzinfo``
object is a :pypi:`pytz` timezone (which predates :pep:`495`).

.. _v6.24.4:

-------------------
6.24.4 - 2021-11-15
-------------------

This patch gives Hypothesis it's own internal :class:`~random.Random` instance,
ensuring that test suites which reset the global random state don't induce
weird correlations between property-based tests (:issue:`2135`).

.. _v6.24.3:

-------------------
6.24.3 - 2021-11-13
-------------------

This patch updates documentation of :func:`~hypothesis.note`
(:issue:`3147`).

.. _v6.24.2:

-------------------
6.24.2 - 2021-11-05
-------------------

This patch updates internal testing for the :ref:`Array API extra <array-api>`
to be consistent with new specification changes: ``sum()`` not accepting
boolean arrays (`#234 <https://github.com/data-apis/array-api/pull/234>`_),
``unique()`` split into separate functions
(`#275 <https://github.com/data-apis/array-api/pull/275>`_), and treating NaNs
as distinct (`#310 <https://github.com/data-apis/array-api/pull/310>`_). It has
no user visible impact.

.. _v6.24.1:

-------------------
6.24.1 - 2021-11-01
-------------------

This patch updates our vendored `list of top-level domains <https://www.iana.org/domains/root/db>`__,
which is used by the provisional :func:`~hypothesis.provisional.domains` strategy.

.. _v6.24.0:

-------------------
6.24.0 - 2021-10-23
-------------------

This patch updates our vendored `list of top-level domains
<https://data.iana.org/TLD/tlds-alpha-by-domain.txt>`__, which is used
by the provisional :func:`~hypothesis.provisional.domains` strategy.

(did you know that gTLDs can be both `added <https://newgtlds.icann.org/en/>`__
and `removed <https://www.icann.org/resources/pages/gtld-registry-agreement-termination-2015-10-09-en>`__?)

.. _v6.23.4:

-------------------
6.23.4 - 2021-10-20
-------------------

This patch adds an error for when ``shapes`` in :func:`xps.arrays()` is not
passed as either a valid shape or strategy.

.. _v6.23.3:

-------------------
6.23.3 - 2021-10-18
-------------------

This patch updates our formatting with :pypi:`shed`.

.. _v6.23.2:

-------------------
6.23.2 - 2021-10-08
-------------------

This patch replaces external links to :doc:`NumPy <numpy:index>` API docs
with :mod:`sphinx.ext.intersphinx` cross-references. It is purely a documentation improvement.

.. _v6.23.1:

-------------------
6.23.1 - 2021-09-29
-------------------

This patch cleans up internal logic for :func:`xps.arrays()`. There is no
user-visible change.

.. _v6.23.0:

-------------------
6.23.0 - 2021-09-26
-------------------

This release follows :pypi:`pytest` in considering :class:`SystemExit` and
:class:`GeneratorExit` exceptions to be test failures, meaning that we will
shink to minimal examples and check for flakiness even though they subclass
:class:`BaseException` directly (:issue:`2223`).

:class:`KeyboardInterrupt` continues to interrupt everything, and will be
re-raised immediately.

.. _v6.22.0:

-------------------
6.22.0 - 2021-09-24
-------------------

This release adds :class:`~hypothesis.extra.django.LiveServerTestCase` and
:class:`~hypothesis.extra.django.StaticLiveServerTestCase` for django test.
Thanks to Ivan Tham for this feature!

.. _v6.21.6:

-------------------
6.21.6 - 2021-09-19
-------------------

This patch fixes some new linter warnings such as :pypi:`flake8-bugbear`'s
``B904`` for explicit exception chaining, so tracebacks might be a bit nicer.

.. _v6.21.5:

-------------------
6.21.5 - 2021-09-16
-------------------

This release fixes ``None`` being inferred as the float64 dtype in
:func:`~xps.from_dtype()` and :func:`~xps.arrays()` from the
:ref:`Array API extra <array-api>`.

.. _v6.21.4:

-------------------
6.21.4 - 2021-09-16
-------------------

This release fixes the type hint for the
:func:`@given() <hypothesis.given>` decorator
when decorating an ``async`` function (:issue:`3099`).

.. _v6.21.3:

-------------------
6.21.3 - 2021-09-15
-------------------

This release improves Ghostwritten tests for builtins (:issue:`2977`).

.. _v6.21.2:

-------------------
6.21.2 - 2021-09-15
-------------------

This release deprecates use of both ``min_dims > len(shape)`` and
``max_dims > len(shape)`` when ``allow_newaxis == False`` in
:func:`~hypothesis.extra.numpy.basic_indices` (:issue:`3091`).

.. _v6.21.1:

-------------------
6.21.1 - 2021-09-13
-------------------

This release improves the behaviour of :func:`~hypothesis.strategies.builds`
and :func:`~hypothesis.strategies.from_type` in certain situations involving
decorators (:issue:`2495` and :issue:`3029`).

.. _v6.21.0:

-------------------
6.21.0 - 2021-09-11
-------------------

This release introduces strategies for array/tensor libraries adopting the
`Array API standard <https://data-apis.org/>`__ (:issue:`3037`).
They are available in :ref:`the hypothesis.extra.array_api extra <array-api>`,
and work much like the existing :doc:`strategies for NumPy <numpy>`.

.. _v6.20.1:

-------------------
6.20.1 - 2021-09-10
-------------------

This patch fixes :issue:`961`, where calling ``given()`` inline on a
bound method would fail to handle the ``self`` argument correctly.

.. _v6.20.0:

-------------------
6.20.0 - 2021-09-09
-------------------

This release allows :func:`~hypothesis.strategies.slices` to generate ``step=None``,
and fixes an off-by-one error where the ``start`` index could be equal to ``size``.
This works fine for all Python sequences and Numpy arrays, but is undefined behaviour
in the `Array API standard <https://data-apis.org/>`__ (see :pull:`3065`).

.. _v6.19.0:

-------------------
6.19.0 - 2021-09-08
-------------------

This release makes :doc:`stateful testing <stateful>` more likely to tell you
if you do something unexpected and unsupported:

- The :obj:`~hypothesis.HealthCheck.return_value` health check now applies to
  :func:`~hypothesis.stateful.rule` and :func:`~hypothesis.stateful.initialize`
  rules, if they don't have ``target`` bundles, as well as
  :func:`~hypothesis.stateful.invariant`.
- Using a :func:`~hypothesis.stateful.consumes` bundle as a ``target`` is
  deprecated, and will be an error in a future version.

If existing code triggers these new checks, check for related bugs and
misunderstandings - these patterns *never* had any effect.

.. _v6.18.0:

-------------------
6.18.0 - 2021-09-06
-------------------

This release teaches :func:`~hypothesis.strategies.from_type` a neat trick:
when resolving an :obj:`python:typing.Annotated` type, if one of the annotations
is a strategy object we use that as the inferred strategy.  For example:

.. code-block:: python

    PositiveInt = Annotated[int, st.integers(min_value=1)]

If there are multiple strategies, we use the last outer-most annotation.
See :issue:`2978` and :pull:`3082` for discussion.

*Requires Python 3.9 or later for*
:func:`get_type_hints(..., include_extras=False) <typing.get_type_hints>`.

.. _v6.17.4:

-------------------
6.17.4 - 2021-08-31
-------------------

This patch makes unique :func:`~hypothesis.extra.numpy.arrays` much more
efficient, especially when there are only a few valid elements - such as
for eight-bit integers (:issue:`3066`).

.. _v6.17.3:

-------------------
6.17.3 - 2021-08-30
-------------------

This patch fixes the repr of :func:`~hypothesis.extra.numpy.array_shapes`.

.. _v6.17.2:

-------------------
6.17.2 - 2021-08-30
-------------------

This patch wraps some internal helper code in our proxies decorator to prevent
mutations of method docstrings carrying over to other instances of the respective
methods.

.. _v6.17.1:

-------------------
6.17.1 - 2021-08-29
-------------------

This patch moves some internal helper code in preparation for :issue:`3065`.
There is no user-visible change, unless you depended on undocumented internals.

.. _v6.17.0:

-------------------
6.17.0 - 2021-08-27
-------------------

This release adds type annotations to the :doc:`stateful testing <stateful>` API.

Thanks to Ruben Opdebeeck for this contribution!

.. _v6.16.0:

-------------------
6.16.0 - 2021-08-27
-------------------

This release adds the :class:`~hypothesis.strategies.DrawFn` type as a reusable
type hint for the ``draw`` argument of
:func:`@composite <hypothesis.strategies.composite>` functions.

Thanks to Ruben Opdebeeck for this contribution!

.. _v6.15.0:

-------------------
6.15.0 - 2021-08-22
-------------------

This release emits a more useful error message when :func:`@given() <hypothesis.given>`
is applied to a coroutine function, i.e. one defined using ``async def`` (:issue:`3054`).

This was previously only handled by the generic :obj:`~hypothesis.HealthCheck.return_value`
health check, which doesn't direct you to use either :ref:`a custom executor <custom-function-execution>`
or a library such as :pypi:`pytest-trio` or :pypi:`pytest-asyncio` to handle it for you.

.. _v6.14.9:

-------------------
6.14.9 - 2021-08-20
-------------------

This patch fixes a regression in Hypothesis 6.14.8, where :func:`~hypothesis.strategies.from_type`
failed to resolve types which inherit from multiple parametrised generic types,
affecting the :pypi:`returns` package (:issue:`3060`).

.. _v6.14.8:

-------------------
6.14.8 - 2021-08-16
-------------------

This patch ensures that registering a strategy for a subclass of a a parametrised
generic type such as ``class Lines(Sequence[str]):`` will not "leak" into unrelated
strategies such as ``st.from_type(Sequence[int])`` (:issue:`2951`).
Unfortunately this fix requires :pep:`560`, meaning Python 3.7 or later.

.. _v6.14.7:

-------------------
6.14.7 - 2021-08-14
-------------------

This patch fixes :issue:`3050`, where :pypi:`attrs` classes could
cause an internal error in the :doc:`ghostwriter <ghostwriter>`.

.. _v6.14.6:

-------------------
6.14.6 - 2021-08-07
-------------------

This patch improves the error message for :issue:`3016`, where :pep:`585`
builtin generics with self-referential forward-reference strings cannot be
resolved to a strategy by :func:`~hypothesis.strategies.from_type`.

.. _v6.14.5:

-------------------
6.14.5 - 2021-07-27
-------------------

This patch fixes ``hypothesis.strategies._internal.types.is_a_new_type``.
It was failing on Python ``3.10.0b4``, where ``NewType`` is a function.

.. _v6.14.4:

-------------------
6.14.4 - 2021-07-26
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` and
:func:`~hypothesis.strategies.register_type_strategy` for
:obj:`python:typing.NewType` on Python 3.10, which changed the
underlying implementation (see :bpo:`44353` for details).

.. _v6.14.3:

-------------------
6.14.3 - 2021-07-18
-------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.14.2:

-------------------
6.14.2 - 2021-07-12
-------------------

This patch ensures that we shorten tracebacks for tests which fail due
to inconsistent data generation between runs (i.e. raise ``Flaky``).

.. _v6.14.1:

-------------------
6.14.1 - 2021-07-02
-------------------

This patch updates some internal type annotations.
There is no user-visible change.

.. _v6.14.0:

-------------------
6.14.0 - 2021-06-09
-------------------

The :ref:`explain phase <phases>` now requires shrinking to be enabled,
and will be automatically skipped for deadline-exceeded errors.

.. _v6.13.14:

--------------------
6.13.14 - 2021-06-04
--------------------

This patch improves the :func:`~hypothesis.strategies.tuples` strategy
type annotations, to preserve the element types for up to length-five
tuples (:issue:`3005`).

As for :func:`~hypothesis.strategies.one_of`, this is the best we can do
before a `planned extension <https://mail.python.org/archives/list/typing-sig@python.org/thread/LOQFV3IIWGFDB7F5BDX746EZJG4VVBI3/>`__
to :pep:`646` is released, hopefully in Python 3.11.

.. _v6.13.13:

--------------------
6.13.13 - 2021-06-04
--------------------

This patch teaches :doc:`the Ghostwriter <ghostwriter>` how to find
:doc:`custom ufuncs <numpy:reference/ufuncs>` from *any* module that defines them,
and that ``yaml.unsafe_load()`` does not undo ``yaml.safe_load()``.

.. _v6.13.12:

--------------------
6.13.12 - 2021-06-03
--------------------

This patch reduces the amount of internal code excluded from our test suite's
code coverage checks.

There is no user-visible change.

.. _v6.13.11:

--------------------
6.13.11 - 2021-06-02
--------------------

This patch removes some old internal helper code that previously existed
to make Python 2 compatibility easier.

There is no user-visible change.

.. _v6.13.10:

--------------------
6.13.10 - 2021-05-30
--------------------

This release adjusts some internal code to help make our test suite more
reliable.

There is no user-visible change.

.. _v6.13.9:

-------------------
6.13.9 - 2021-05-30
-------------------

This patch cleans up some internal code related to filtering strategies.

There is no user-visible change.

.. _v6.13.8:

-------------------
6.13.8 - 2021-05-28
-------------------

This patch slightly improves the performance of some internal code for
generating integers.

.. _v6.13.7:

-------------------
6.13.7 - 2021-05-27
-------------------

This patch fixes a bug in :func:`~hypothesis.strategies.from_regex` that
caused ``from_regex("", fullmatch=True)`` to unintentionally generate non-empty
strings (:issue:`4982`).

The only strings that completely match an empty regex pattern are empty
strings.

.. _v6.13.6:

-------------------
6.13.6 - 2021-05-26
-------------------

This patch fixes a bug that caused :func:`~hypothesis.strategies.integers`
to shrink towards negative values instead of positive values in some cases.

.. _v6.13.5:

-------------------
6.13.5 - 2021-05-24
-------------------

This patch fixes rare cases where ``hypothesis write --binary-op`` could
print :doc:`reproducing instructions <reproducing>` from the internal
search for an identity element.

.. _v6.13.4:

-------------------
6.13.4 - 2021-05-24
-------------------

This patch removes some unnecessary intermediate list-comprehensions,
using the latest versions of :pypi:`pyupgrade` and :pypi:`shed`.

.. _v6.13.3:

-------------------
6.13.3 - 2021-05-23
-------------------

This patch adds a ``.hypothesis`` property to invalid test functions, bringing
them inline with valid tests and fixing a bug where :pypi:`pytest-asyncio` would
swallow the real error message and mistakenly raise a version incompatibility
error.

.. _v6.13.2:

-------------------
6.13.2 - 2021-05-23
-------------------

Some of Hypothesis's numpy/pandas strategies use a ``fill`` argument to speed
up generating large arrays, by generating a single fill value and sharing that
value among many array slots instead of filling every single slot individually.

When no ``fill`` argument is provided, Hypothesis tries to detect whether it is
OK to automatically use the ``elements`` argument as a fill strategy, so that
it can still use the faster approach.

This patch fixes a bug that would cause that optimization to trigger in some
cases where it isn't 100% guaranteed to be OK.

If this makes some of your numpy/pandas tests run more slowly, try adding an
explicit ``fill`` argument to the relevant strategies to ensure that Hypothesis
always uses the faster approach.

.. _v6.13.1:

-------------------
6.13.1 - 2021-05-20
-------------------

This patch strengthens some internal import-time consistency checks for the
built-in strategies.

There is no user-visible change.

.. _v6.13.0:

-------------------
6.13.0 - 2021-05-18
-------------------

This release adds URL fragment generation to the :func:`~hypothesis.provisional.urls`
strategy (:issue:`2908`). Thanks to Pax (R. Margret) for contributing this patch at the
`PyCon US Mentored Sprints <https://us.pycon.org/2021/summits/mentored-sprints/>`__!

.. _v6.12.1:

-------------------
6.12.1 - 2021-05-17
-------------------

This patch fixes :issue:`2964`, where ``.map()`` and ``.filter()`` methods
were omitted from the ``repr()`` of :func:`~hypothesis.strategies.just` and
:func:`~hypothesis.strategies.sampled_from` strategies, since
:ref:`version 5.43.7 <v5.43.7>`.

.. _v6.12.0:

-------------------
6.12.0 - 2021-05-06
-------------------

This release automatically rewrites some simple filters, such as
``integers().filter(lambda x: x > 9)`` to the more efficient
``integers(min_value=10)``, based on the AST of the predicate.

We continue to recommend using the efficient form directly wherever
possible, but this should be useful for e.g. :pypi:`pandera` "``Checks``"
where you already have a simple predicate and translating manually
is really annoying.  See :issue:`2701` for ideas about floats and
simple text strategies.

.. _v6.11.0:

-------------------
6.11.0 - 2021-05-06
-------------------

:func:`hypothesis.target` now returns the ``observation`` value,
allowing it to be conveniently used inline in expressions such as
``assert target(abs(a - b)) < 0.1``.

.. _v6.10.1:

-------------------
6.10.1 - 2021-04-26
-------------------

This patch fixes a deprecation warning if you're using recent versions
of :pypi:`importlib-metadata` (:issue:`2934`), which we use to load
:ref:`third-party plugins <entry-points>` such as `Pydantic's integration
<https://docs.pydantic.dev/latest/hypothesis_plugin/>`__.
On older versions of :pypi:`importlib-metadata`, there is no change and
you don't need to upgrade.

.. _v6.10.0:

-------------------
6.10.0 - 2021-04-17
-------------------

This release teaches the :doc:`Ghostwriter <ghostwriter>` to read parameter
types from Sphinx, Google, or Numpy-style structured docstrings, and improves
some related heuristics about how to test scientific and numerical programs.

.. _v6.9.2:

------------------
6.9.2 - 2021-04-15
------------------

This release improves the :doc:`Ghostwriter's <ghostwriter>` handling
of exceptions, by reading ``:raises ...:`` entries in function docstrings
and ensuring that we don't suppresss the error raised by test assertions.

.. _v6.9.1:

------------------
6.9.1 - 2021-04-12
------------------

This patch updates our autoformatting tools, improving our code style without any API changes.

.. _v6.9.0:

------------------
6.9.0 - 2021-04-11
------------------

This release teaches :func:`~hypothesis.strategies.from_type` how to see
through :obj:`python:typing.Annotated`.  Thanks to Vytautas Strimaitis
for reporting and fixing :issue:`2919`!

.. _v6.8.12:

-------------------
6.8.12 - 2021-04-11
-------------------

If :pypi:`rich` is installed, the :command:`hypothesis write` command
will use it to syntax-highlight the :doc:`Ghostwritten <ghostwriter>`
code.

.. _v6.8.11:

-------------------
6.8.11 - 2021-04-11
-------------------

This patch improves an error message from :func:`~hypothesis.strategies.builds`
when :func:`~hypothesis.strategies.from_type` would be more suitable (:issue:`2930`).

.. _v6.8.10:

-------------------
6.8.10 - 2021-04-11
-------------------

This patch updates the type annotations for :func:`~hypothesis.extra.numpy.arrays` to reflect that
``shape: SearchStrategy[int]`` is supported.

.. _v6.8.9:

------------------
6.8.9 - 2021-04-07
------------------

This patch fixes :func:`~hypothesis.strategies.from_type` with
:mod:`abstract types <python:abc>` which have either required but
non-type-annotated arguments to ``__init__``, or where
:func:`~hypothesis.strategies.from_type` can handle some concrete
subclasses but not others.

.. _v6.8.8:

------------------
6.8.8 - 2021-04-07
------------------

This patch teaches :command:`hypothesis write` to check for possible roundtrips
in several more cases, such as by looking for an inverse in the module which
defines the function to test.

.. _v6.8.7:

------------------
6.8.7 - 2021-04-07
------------------

This patch adds a more helpful error message if you try to call
:func:`~hypothesis.strategies.sampled_from` on an :class:`~python:enum.Enum`
which has no members, but *does* have :func:`~python:dataclasses.dataclass`-style
annotations (:issue:`2923`).

.. _v6.8.6:

------------------
6.8.6 - 2021-04-06
------------------

The :func:`~hypothesis.strategies.fixed_dictionaries` strategy now preserves
dict iteration order instead of sorting the keys.  This also affects the
pretty-printing of keyword arguments to :func:`@given() <hypothesis.given>`
(:issue:`2913`).

.. _v6.8.5:

------------------
6.8.5 - 2021-04-05
------------------

This patch teaches :command:`hypothesis write` to default to ghostwriting
tests with ``--style=pytest`` only if :pypi:`pytest` is installed, or
``--style=unittest`` otherwise.

.. _v6.8.4:

------------------
6.8.4 - 2021-04-01
------------------

This patch adds type annotations for the :class:`~hypothesis.settings` decorator,
to avoid an error when running mypy in strict mode.

.. _v6.8.3:

------------------
6.8.3 - 2021-03-28
------------------

This patch improves the :doc:`Ghostwriter's <ghostwriter>` handling
of strategies to generate various fiddly types including frozensets,
keysviews, valuesviews, regex matches and patterns, and so on.

.. _v6.8.2:

------------------
6.8.2 - 2021-03-27
------------------

This patch fixes some internal typos.  There is no user-visible change.

.. _v6.8.1:

------------------
6.8.1 - 2021-03-14
------------------

This patch lays more groundwork for filter rewriting (:issue:`2701`).
There is no user-visible change... yet.

.. _v6.8.0:

------------------
6.8.0 - 2021-03-11
------------------

This release :func:`registers <hypothesis.strategies.register_type_strategy>` the
remaining builtin types, and teaches :func:`~hypothesis.strategies.from_type` to
try resolving :class:`~python:typing.ForwardRef` and :class:`~python:typing.Type`
references to built-in types.

.. _v6.7.0:

------------------
6.7.0 - 2021-03-10
------------------

This release teaches :class:`~hypothesis.stateful.RuleBasedStateMachine` to avoid
checking :func:`~hypothesis.stateful.invariant`\ s until all
:func:`~hypothesis.stateful.initialize` rules have been run.  You can enable checking
of specific invariants for incompletely initialized machines by using
``@invariant(check_during_init=True)`` (:issue:`2868`).

In previous versions, it was possible if awkward to implement this behaviour
using :func:`~hypothesis.stateful.precondition` and an auxiliary variable.

.. _v6.6.1:

------------------
6.6.1 - 2021-03-09
------------------

This patch improves the error message when :func:`~hypothesis.strategies.from_type`
fails to resolve a forward-reference inside a :class:`python:typing.Type`
such as ``Type["int"]`` (:issue:`2565`).

.. _v6.6.0:

------------------
6.6.0 - 2021-03-07
------------------

This release makes it an explicit error to apply :func:`~hypothesis.stateful.invariant`
to a :func:`~hypothesis.stateful.rule` or :func:`~hypothesis.stateful.initialize` rule
in :doc:`stateful testing <stateful>`.  Such a combination had unclear semantics,
especially in combination with :func:`~hypothesis.stateful.precondition`, and was never
meant to be allowed (:issue:`2681`).

.. _v6.5.0:

------------------
6.5.0 - 2021-03-07
------------------

This release adds :ref:`the explain phase <phases>`, in which Hypothesis
attempts to explain *why* your test failed by pointing to suspicious lines
of code (i.e. those which were always, and only, run on failing inputs).
We plan to include "generalising" failing examples in this phase in a
future release (:issue:`2192`).

.. _v6.4.3:

------------------
6.4.3 - 2021-03-04
------------------

This patch fixes :issue:`2794`, where nesting :func:`~hypothesis.strategies.deferred`
strategies within :func:`~hypothesis.strategies.recursive` strategies could
trigger an internal assertion.  While it was always possible to get the same
results from a more sensible strategy, the convoluted form now works too.

.. _v6.4.2:

------------------
6.4.2 - 2021-03-04
------------------

This patch fixes several problems with ``mypy`` when `--no-implicit-reexport <https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-no-implicit-reexport>`_ was activated in user projects.

Thanks to Nikita Sobolev for fixing :issue:`2884`!

.. _v6.4.1:

------------------
6.4.1 - 2021-03-04
------------------

This patch fixes an exception that occurs when using type unions of
the :pypi:`typing-extensions` ``Literal`` backport on Python 3.6.

Thanks to Ben Anhalt for identifying and fixing this bug.

.. _v6.4.0:

------------------
6.4.0 - 2021-03-02
------------------

This release fixes :doc:`stateful testing methods <stateful>` with multiple
:func:`~hypothesis.stateful.precondition` decorators.  Previously, only the
outer-most precondition was checked (:issue:`2681`).

.. _v6.3.4:

------------------
6.3.4 - 2021-02-28
------------------

This patch refactors some internals of :class:`~hypothesis.stateful.RuleBasedStateMachine`.
There is no change to the public API or behaviour.

.. _v6.3.3:

------------------
6.3.3 - 2021-02-26
------------------

This patch moves some internal code, so that future work can avoid
creating import cycles.  There is no user-visible change.

.. _v6.3.2:

------------------
6.3.2 - 2021-02-25
------------------

This patch enables :func:`~hypothesis.strategies.register_type_strategy` for subclasses of
:class:`python:typing.TypedDict`.  Previously, :func:`~hypothesis.strategies.from_type`
would ignore the registered strategy (:issue:`2872`).

Thanks to Ilya Lebedev for identifying and fixing this bug!

.. _v6.3.1:

------------------
6.3.1 - 2021-02-24
------------------

This release lays the groundwork for automatic rewriting of simple filters,
for example converting ``integers().filter(lambda x: x > 9)`` to
``integers(min_value=10)``.

Note that this is **not supported yet**, and we will continue to recommend
writing the efficient form directly wherever possible - predicate rewriting
is provided mainly for the benefit of downstream libraries which would
otherwise have to implement it for themselves (e.g. :pypi:`pandera` and
:pypi:`icontract-hypothesis`).  See :issue:`2701` for details.

.. _v6.3.0:

------------------
6.3.0 - 2021-02-20
------------------

The Hypothesis :pypi:`pytest` plugin now requires pytest version 4.6 or later.
If the plugin detects an earlier version of pytest, it will automatically
deactivate itself.

`(4.6.x is the earliest pytest branch that still accepts community bugfixes.)
<https://docs.pytest.org/en/6.2.x/py27-py34-deprecation.html>`__

Hypothesis-based tests should continue to work in earlier versions of
pytest, but enhanced integrations provided by the plugin
(such as ``--hypothesis-show-statistics`` and other command-line flags)
will no longer be available in obsolete pytest versions.

.. _v6.2.0:

------------------
6.2.0 - 2021-02-12
------------------

If you use :pypi:`pytest-html`, Hypothesis now includes the
:ref:`summary statistics for each test <statistics>` in the HTML report,
whether or not the ``--hypothesis-show-statistics`` argument was passed
to show them in the command-line output.

.. _v6.1.1:

------------------
6.1.1 - 2021-01-31
------------------

This patch updates our automatic code formatting to use :pypi:`shed`,
which includes :pypi:`autoflake`, :pypi:`black`, :pypi:`isort`, and
:pypi:`pyupgrade` (:issue:`2780`).

.. _v6.1.0:

------------------
6.1.0 - 2021-01-29
------------------

This release teaches Hypothesis to distinguish between errors based on the
`__cause__ or __context__ of otherwise identical exceptions
<https://docs.python.org/3/library/exceptions.html>`__, which is particularly
useful when internal errors can be wrapped by a library-specific or semantically
appropriate exception such as:

.. code-block:: python

    try:
        do_the_thing(foo, timeout=10)
    except Exception as err:
        raise FooError("Failed to do the thing") from err

Earlier versions of Hypothesis only see the ``FooError``, while we can now
distinguish a ``FooError`` raised because of e.g. an internal assertion from
one raised because of a ``TimeoutExceeded`` exception.

.. _v6.0.4:

------------------
6.0.4 - 2021-01-27
------------------

This release prevents a race condition inside :func:`~hypothesis.strategies.recursive` strategies.
The race condition occurs when the same :func:`~hypothesis.strategies.recursive` strategy is shared among tests
that are running in multiple threads (:issue:`2717`).

.. _v6.0.3:

------------------
6.0.3 - 2021-01-23
------------------

This patch improves the type annotations for :func:`~hypothesis.strategies.one_of`,
by adding overloads to handle up to five distinct arguments as
:obj:`~python:typing.Union` before falling back to :obj:`~python:typing.Any`,
as well as annotating the ``|`` (``__or__``) operator for strategies (:issue:`2765`).

.. _v6.0.2:

------------------
6.0.2 - 2021-01-14
------------------

This release makes some small improvements to how filtered strategies work. It should improve the performance of shrinking filtered strategies,
and may under some (probably rare) circumstances improve the diversity of generated examples.

.. _v6.0.1:

------------------
6.0.1 - 2021-01-13
------------------

This patch fixes an interaction where our :ref:`test statistics <statistics>`
handling made Pytest's ``--junit-xml`` output fail to validate against the
strict ``xunit2`` schema (:issue:`1975`).

.. _v6.0.0:

------------------
6.0.0 - 2021-01-08
------------------

Welcome to the next major version of Hypothesis!

There are no new features here, as we release those in minor versions.
Instead, 6.0 is a chance for us to remove deprecated features (many already
converted into no-ops), and turn a variety of warnings into errors.

If you were running on the last version of Hypothesis 5.x *without any
Hypothesis deprecation warnings*, this will be a very boring upgrade.
**In fact, nothing will change for you at all.**

Changes
~~~~~~~
- Many functions now use :pep:`3102` keyword-only arguments where passing positional
  arguments :ref:`was deprecated since 5.5 <v5.5.0>`.
- :func:`hypothesis.extra.django.from_model` no longer accepts ``model`` as a
  keyword argument, where it could conflict with fields named "model".
- :func:`~hypothesis.strategies.randoms` now defaults to ``use_true_random=False``.
- :func:`~hypothesis.strategies.complex_numbers` no longer accepts
  ``min_magnitude=None``; either use ``min_magnitude=0`` or just omit the argument.
- ``hypothesis.provisional.ip4_addr_strings`` and ``ip6_addr_strings`` are removed
  in favor of :func:`ip_addresses(v=...).map(str) <hypothesis.strategies.ip_addresses>`.
- :func:`~hypothesis.strategies.register_type_strategy` no longer accepts generic
  types with type arguments, which were always pretty badly broken.
- Using function-scoped pytest fixtures is now a health-check error, instead of a warning.

.. tip::
    The :command:`hypothesis codemod` command can automatically refactor your code,
    particularly to convert positional to keyword arguments where those are now
    required.

Hypothesis 5.x
==============

.. _v5.49.0:

-------------------
5.49.0 - 2021-01-07
-------------------

This release adds the
:obj:`~hypothesis.HealthCheck.function_scoped_fixture` health check value,
which can be used to suppress the existing warning that appears when
:func:`@given <hypothesis.given>` is applied to a test that uses pytest
function-scoped fixtures.

(This warning exists because function-scoped fixtures only run once per
function, not once per example, which is usually unexpected and can cause
subtle problems.)

When this warning becomes a health check error in a future release, suppressing
it via Python warning settings will no longer be possible.
In the rare case that once-per-function behaviour is intended, it will still be
possible to use :obj:`~hypothesis.HealthCheck.function_scoped_fixture` to
opt out of the health check error for specific tests.

.. _v5.48.0:

-------------------
5.48.0 - 2021-01-06
-------------------

This release adds :func:`hypothesis.currently_in_test_context`, which can be used
to check whether the calling code is currently running inside an
:func:`@given <hypothesis.given>` or :doc:`stateful <stateful>` test.

This is most useful for third-party integrations and assertion helpers which may
wish to use :func:`~hypothesis.assume` or :func:`~hypothesis.target`, without also
requiring that the helper only be used from property-based tests (:issue:`2581`).

.. _v5.47.0:

-------------------
5.47.0 - 2021-01-05
-------------------

This release upgrades the import logic for :doc:`ghostwritten tests <ghostwriter>`,
handling many cases where imports would previously be missing or from unexpected
locations.

.. _v5.46.0:

-------------------
5.46.0 - 2021-01-04
-------------------

This release upgrades :func:`~hypothesis.strategies.from_type`, to infer
strategies for type-annotated arguments even if they have defaults when
it otherwise falls back to :func:`~hypothesis.strategies.builds`
(:issue:`2708`).

.. _v5.45.0:

-------------------
5.45.0 - 2021-01-04
-------------------

This release adds the :ref:`codemods` extra, which you can use to
check for and automatically fix issues such as use of deprecated
Hypothesis APIs (:issue:`2705`).

.. _v5.44.0:

-------------------
5.44.0 - 2021-01-03
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` with
the :pypi:`typing-extensions` ``Literal`` backport on Python 3.6.

.. _v5.43.9:

-------------------
5.43.9 - 2021-01-02
-------------------

This patch fixes :issue:`2722`, where certain orderings of
:func:`~hypothesis.strategies.register_type_strategy`,
:class:`~python:typing.ForwardRef`, and :func:`~hypothesis.strategies.from_type`
could trigger an internal error.

.. _v5.43.8:

-------------------
5.43.8 - 2021-01-02
-------------------

This patch makes some strategies for collections with a uniqueness constraint
much more efficient, including ``dictionaries(keys=sampled_from(...), values=..)``
and ``lists(tuples(sampled_from(...), ...), unique_by=lambda x: x[0])``.
(related to :issue:`2036`)

.. _v5.43.7:

-------------------
5.43.7 - 2021-01-02
-------------------

This patch extends our faster special case for
:func:`~hypothesis.strategies.sampled_from` elements in unique
:func:`~hypothesis.strategies.lists` to account for chains of
``.map(...)`` and ``.filter(...)`` calls (:issue:`2036`).

.. _v5.43.6:

-------------------
5.43.6 - 2021-01-02
-------------------

This patch improves the type annotations on :func:`~hypothesis.assume`
and :func:`@reproduce_failure() <hypothesis.reproduce_failure>`.

.. _v5.43.5:

-------------------
5.43.5 - 2021-01-01
-------------------

This patch updates our copyright headers to include 2021.  Happy new year!

.. _v5.43.4:

-------------------
5.43.4 - 2020-12-24
-------------------

This change fixes a documentation error in the
:obj:`~hypothesis.settings.database` setting.

The previous documentation suggested that callers could specify a database
path string, or the special string ``":memory:"``, but this setting has
never actually allowed string arguments.

Permitted values are ``None``, and instances of
:class:`~hypothesis.database.ExampleDatabase`.

.. _v5.43.3:

-------------------
5.43.3 - 2020-12-11
-------------------

This patch fixes :issue:`2696`, an internal error triggered when the
:obj:`@example <hypothesis.example>` decorator was used and the
:obj:`~hypothesis.settings.verbosity` setting was ``quiet``.

.. _v5.43.2:

-------------------
5.43.2 - 2020-12-10
-------------------

This patch improves the error message from the
:func:`~hypothesis.extra.pandas.data_frames` strategy when both the ``rows``
and ``columns`` arguments are given, but there is a missing entry in ``rows``
and the corresponding column has no ``fill`` value (:issue:`2678`).

.. _v5.43.1:

-------------------
5.43.1 - 2020-12-10
-------------------

This patch improves the error message if :func:`~hypothesis.strategies.builds`
is passed an :class:`~python:enum.Enum` which cannot be called without arguments,
to suggest using :func:`~hypothesis.strategies.sampled_from` (:issue:`2693`).

.. _v5.43.0:

-------------------
5.43.0 - 2020-12-09
-------------------

This release adds new :func:`~hypothesis.strategies.timezones` and
:func:`~hypothesis.strategies.timezone_keys` strategies (:issue:`2630`)
based on the new :mod:`python:zoneinfo` module in Python 3.9.

``pip install hypothesis[zoneinfo]`` will ensure that you have the
appropriate backports installed if you need them.

.. _v5.42.3:

-------------------
5.42.3 - 2020-12-09
-------------------

This patch fixes an internal error in :func:`~hypothesis.strategies.datetimes`
with ``allow_imaginary=False`` where the ``timezones`` argument can generate
``tzinfo=None`` (:issue:`2662`).

.. _v5.42.2:

-------------------
5.42.2 - 2020-12-09
-------------------

This patch teaches :func:`hypothesis.extra.django.from_field` to infer
more efficient strategies by inspecting (not just filtering by) field
validators for numeric and string fields (:issue:`1116`).

.. _v5.42.1:

-------------------
5.42.1 - 2020-12-09
-------------------

This patch refactors :class:`hypothesis.settings` to use type-annotated
keyword arguments instead of ``**kwargs``, which makes tab-completion
much more useful - as well as type-checkers like :pypi:`mypy`.

.. _v5.42.0:

-------------------
5.42.0 - 2020-12-09
-------------------

This patch teaches the :func:`~hypothesis.extra.ghostwriter.magic` ghostwriter
to recognise "en/de" function roundtrips other than the common encode/decode
pattern, such as encrypt/decrypt or, encipher/decipher.

.. _v5.41.5:

-------------------
5.41.5 - 2020-12-05
-------------------

This patch adds a performance optimisation to avoid saving redundant
seeds when using :ref:`the .fuzz_one_input hook <fuzz_one_input>`.

.. _v5.41.4:

-------------------
5.41.4 - 2020-11-28
-------------------

This patch fixes :issue:`2657`, where passing unicode patterns compiled with
:obj:`python:re.IGNORECASE` to :func:`~hypothesis.strategies.from_regex` could
trigger an internal error when casefolding a character creates a longer string
(e.g. ``"\u0130".lower() -> "i\u0370"``).

.. _v5.41.3:

-------------------
5.41.3 - 2020-11-18
-------------------

This patch adds a final fallback clause to :ref:`our plugin logic <entry-points>`
to fail with a warning rather than error on Python < 3.8 when neither the
:pypi:`importlib-metadata` (preferred) or :pypi:`setuptools` (fallback)
packages are available.

.. _v5.41.2:

-------------------
5.41.2 - 2020-11-08
-------------------

This patch fixes :func:`~hypothesis.provisional.urls` strategy ensuring that
``~`` (tilde) is treated as one of the url-safe characters (:issue:`2658`).

.. _v5.41.1:

-------------------
5.41.1 - 2020-11-03
-------------------

This patch improves our :ref:`CLI help and documentation <hypothesis-cli>`.

.. _v5.41.0:

-------------------
5.41.0 - 2020-10-30
-------------------

Hypothesis now shrinks examples where the error is raised while drawing from
a strategy.  This makes complicated custom strategies *much* easier to debug,
at the cost of a slowdown for use-cases where you catch and ignore such errors.

.. _v5.40.0:

-------------------
5.40.0 - 2020-10-30
-------------------

This release teaches :func:`~hypothesis.strategies.from_type` how to handle
:class:`~python:typing.ChainMap`, :class:`~python:typing.Counter`,
:class:`~python:typing.Deque`, :class:`~python:typing.Generator`,
:class:`~python:typing.Match`, :class:`~python:typing.OrderedDict`,
:class:`~python:typing.Pattern`, and :class:`~python:collections.abc.Set`
(:issue:`2654`).

.. _v5.39.0:

-------------------
5.39.0 - 2020-10-30
-------------------

:func:`~hypothesis.strategies.from_type` now knows how to resolve :pep:`585`
parameterized standard collection types, which are new in Python 3.9
(:issue:`2629`).

.. _v5.38.1:

-------------------
5.38.1 - 2020-10-26
-------------------

This patch fixes :func:`~hypothesis.strategies.builds`, so that when passed
:obj:`~hypothesis.infer` for an argument with a non-:obj:`~python:typing.Optional`
type annotation and a default value of ``None`` to build a class which defines
an explicit ``__signature__`` attribute, either ``None`` or that type may be
generated.

This is unlikely to happen unless you are using :pypi:`pydantic` (:issue:`2648`).

.. _v5.38.0:

-------------------
5.38.0 - 2020-10-24
-------------------

This release improves our support for :func:`@st.composite <hypothesis.strategies.composite>`
on a :obj:`python:classmethod` or :obj:`python:staticmethod` (:issue:`2578`).

.. _v5.37.5:

-------------------
5.37.5 - 2020-10-24
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` with
:class:`Iterable[T] <python:typing.Iterable>` (:issue:`2645`).

.. _v5.37.4:

-------------------
5.37.4 - 2020-10-20
-------------------

This patch teaches the :func:`~hypothesis.extra.ghostwriter.magic` ghostwriter
to recognise that pairs of functions like :func:`~python:colorsys.rgb_to_hsv`
and :func:`~python:colorsys.hsv_to_rgb` should
:func:`~hypothesis.extra.ghostwriter.roundtrip`.

.. _v5.37.3:

-------------------
5.37.3 - 2020-10-15
-------------------

This patch improves :func:`~hypothesis.strategies.builds` and
:func:`~hypothesis.strategies.from_type` support for explicitly defined ``__signature__``
attributes, from :ref:`version 5.8.3 <v5.8.3>`, to support generic types from the
:mod:`python:typing` module.

Thanks to Rónán Carrigan for identifying and fixing this problem!

.. _v5.37.2:

-------------------
5.37.2 - 2020-10-14
-------------------

This patch fixes :func:`~hypothesis.extra.lark.from_lark` with version
0.10.1+ of the :pypi:`lark-parser` package.

.. _v5.37.1:

-------------------
5.37.1 - 2020-10-07
-------------------

This patch fixes some broken links in the :mod:`~hypothesis.extra.lark`
extra documentation.

.. _v5.37.0:

-------------------
5.37.0 - 2020-10-03
-------------------

This release adds a new :class:`~hypothesis.extra.redis.RedisExampleDatabase`,
along with the :class:`~hypothesis.database.ReadOnlyDatabase`
and :class:`~hypothesis.database.MultiplexedDatabase` helpers, to support
team workflows where failing examples can be seamlessly shared between everyone
on the team - and your CI servers or buildbots.

.. _v5.36.2:

-------------------
5.36.2 - 2020-10-02
-------------------

This patch ensures that if the :ref:`"hypothesis" entry point <entry-points>`
is callable, we call it after importing it.  You can still use non-callable
entry points (like modules), which are only imported.

We also prefer `importlib.metadata <https://docs.python.org/3/library/importlib.metadata.html>`__
or :pypi:`the backport <importlib-metadata>` over `pkg_resources
<https://setuptools.pypa.io/en/latest/pkg_resources.html>`__,
which makes ``import hypothesis`` around 200 milliseconds faster
(:issue:`2571`).

.. _v5.36.1:

-------------------
5.36.1 - 2020-09-25
-------------------

This patch adds some helpful suggestions to error messages you might see
while learning to use the :obj:`@example() <hypothesis.example>` decorator
(:issue:`2611`) or the :func:`~hypothesis.strategies.one_of` strategy.

.. _v5.36.0:

-------------------
5.36.0 - 2020-09-24
-------------------

This release upgrades the :func:`~hypothesis.extra.numpy.from_dtype` strategy
to pass optional ``**kwargs`` to the inferred strategy, and upgrades the
:func:`~hypothesis.extra.numpy.arrays` strategy to accept an ``elements=kwargs``
dict to pass through to :func:`~hypothesis.extra.numpy.from_dtype`.

``arrays(floating_dtypes(), shape, elements={"min_value": -10, "max_value": 10})``
is a particularly useful pattern, as it allows for any floating dtype without
triggering the roundoff warning for smaller types or sacrificing variety for
larger types (:issue:`2552`).

.. _v5.35.4:

-------------------
5.35.4 - 2020-09-21
-------------------

This patch reformats our code with the latest :pypi:`black` to
take advantage of the support for magic trailing commas.

.. _v5.35.3:

-------------------
5.35.3 - 2020-09-15
-------------------

This release significantly improves the performance of Hypothesis's internal
implementation of automaton learning. However this code does not run as part
of the user-accessible API so this has no user-visible impact.

.. _v5.35.2:

-------------------
5.35.2 - 2020-09-14
-------------------

This patch ensures that, when the ``generate`` :obj:`~hypothesis.settings.phases`
is disabled, we can replay up to :obj:`~hypothesis.settings.max_examples` examples
from the database - which is very useful when
:ref:`using Hypothesis with a fuzzer <fuzz_one_input>`.

Thanks to Afrida Tabassum for fixing :issue:`2585`!

.. _v5.35.1:

-------------------
5.35.1 - 2020-09-14
-------------------

This patch changes some internal :obj:`python:struct.Struct.format` strings
from ``bytes`` to ``str``, to avoid :class:`python:BytesWarning` when running
`python -bb <https://docs.python.org/3/using/cmdline.html#cmdoption-b>`__.

Thanks to everyone involved in `pytest-xdist issue 596
<https://github.com/pytest-dev/pytest-xdist/issues/596>`__,
:bpo:`16349`, :bpo:`21071`, and :bpo:`41777` for their work on this -
it was a remarkably subtle issue!

.. _v5.35.0:

-------------------
5.35.0 - 2020-09-11
-------------------

The :func:`~hypothesis.target` function now accepts integers as well as floats.

.. _v5.34.1:

-------------------
5.34.1 - 2020-09-11
-------------------

This patch adds explicit :obj:`~python:typing.Optional` annotations to our public API,
to better support users who run :pypi:`mypy` with ``--strict`` or ``no_implicit_optional=True``.

Thanks to Krzysztof Przybyła for bringing this to our attention and writing the patch!

.. _v5.34.0:

-------------------
5.34.0 - 2020-09-11
-------------------

This release drops support for Python 3.5, which `reached end of life upstream
<https://devguide.python.org/#status-of-python-branches>`__ on 2020-09-13.

.. _v5.33.2:

-------------------
5.33.2 - 2020-09-09
-------------------

This patch fixes a problem with :func:`~hypothesis.strategies.builds` that was not able to
generate valid data for annotated classes with constructors.

Thanks to Nikita Sobolev for fixing :issue:`2603`!

.. _v5.33.1:

-------------------
5.33.1 - 2020-09-07
-------------------

This patch improves the error message from the :command:`hypothesis write`
command if :pypi:`black` (required for the :doc:`ghostwriter <ghostwriter>`)
is not installed.

Thanks to Nikita Sobolev for fixing :issue:`2604`!

.. _v5.33.0:

-------------------
5.33.0 - 2020-09-06
-------------------

When reporting failing examples, or tried examples in verbose mode, Hypothesis now
identifies which were from :obj:`@example(...) <hypothesis.example>` explicit examples.

.. _v5.32.1:

-------------------
5.32.1 - 2020-09-06
-------------------

This patch contains some internal refactoring.
Thanks to Felix Sheldon for fixing :issue:`2516`!

.. _v5.32.0:

-------------------
5.32.0 - 2020-09-04
-------------------

An array drawn from :func:`~hypothesis.extra.numpy.arrays` will own its own memory; previously most arrays returned by
this strategy were views.

.. _v5.31.0:

-------------------
5.31.0 - 2020-09-04
-------------------

:func:`~hypothesis.strategies.builds` will use the ``__signature__`` attribute of
the target, if it exists, to retrieve type hints.
Previously :func:`python:typing.get_type_hints`, was used by default.
If argument names varied between the ``__annotations__`` and ``__signature__``,
they would not be supplied to the target.

This was particularly an issue for :pypi:`pydantic` models which use an
`alias generator <https://docs.pydantic.dev/latest/api/config/#pydantic.alias_generators>`__.

.. _v5.30.1:

-------------------
5.30.1 - 2020-09-04
-------------------

This patch makes the :doc:`ghostwriter <ghostwriter>` much more robust when
passed unusual modules.

- improved support for non-resolvable type annotations
- :func:`~hypothesis.extra.ghostwriter.magic` can now write
  :func:`~hypothesis.extra.ghostwriter.equivalent` tests
- running :func:`~hypothesis.extra.ghostwriter.magic` on modules where some
  names in ``__all__`` are undefined skips such names, instead of raising an error
- :func:`~hypothesis.extra.ghostwriter.magic` now knows to skip mocks
- improved handling of import-time errors found by the ghostwriter CLI

.. _v5.30.0:

-------------------
5.30.0 - 2020-08-30
-------------------

:func:`~hypothesis.strategies.register_type_strategy` now supports
:class:`python:typing.TypeVar`, which was previously hard-coded, and allows a
variety of types to be generated for an unconstrained :class:`~python:typing.TypeVar`
instead of just :func:`~hypothesis.strategies.text`.

Thanks again to Nikita Sobolev for all your work on advanced types!

.. _v5.29.4:

-------------------
5.29.4 - 2020-08-28
-------------------

This release fixes some hard to trigger bugs in Hypothesis's automata learning
code. This code is only run as part of the Hypothesis build process, and not
for user code, so this release has no user visible impact.

.. _v5.29.3:

-------------------
5.29.3 - 2020-08-27
-------------------

This patch adds type annotations to the :doc:`hypothesis.database <database>`
module.  There is no runtime change, but your typechecker might notice.

.. _v5.29.2:

-------------------
5.29.2 - 2020-08-27
-------------------

This patch tracks some additional information in Hypothesis internals,
and has no user-visible impact.

.. _v5.29.1:

-------------------
5.29.1 - 2020-08-27
-------------------

This release fixes a bug in some Hypothesis internal support code for learning
automata. This mostly doesn't have any user visible impact, although it slightly
affects the learned shrink passes so shrinking may be subtly different.

.. _v5.29.0:

-------------------
5.29.0 - 2020-08-24
-------------------

This release adds support for :ref:`entry-points`, which allows for smoother
integration of third-party Hypothesis extensions and external libraries.
Unless you're publishing a library with Hypothesis integration, you'll
probably only ever use this indirectly!

.. _v5.28.0:

-------------------
5.28.0 - 2020-08-24
-------------------

:func:`~hypothesis.strategies.from_type` can now resolve :class:`~python:typing.TypeVar`
instances when the ``bound`` is a :class:`~python:typing.ForwardRef`, so long as that name
is in fact defined in the same module as the typevar (no ``TYPE_CHECKING`` tricks, sorry).
This feature requires Python 3.7 or later.

Thanks to Zac Hatfield-Dodds and Nikita Sobolev for this feature!

.. _v5.27.0:

-------------------
5.27.0 - 2020-08-20
-------------------

This patch adds two new :doc:`ghostwriters <ghostwriter>` to test
:wikipedia:`binary operations <Binary_operation>`, like :func:`python:operator.add`,
and Numpy :doc:`ufuncs <numpy:reference/ufuncs>` and :doc:`gufuncs
<numpy:reference/c-api/generalized-ufuncs>` like :data:`np.matmul() <numpy:numpy.matmul>`.

.. _v5.26.1:

-------------------
5.26.1 - 2020-08-19
-------------------

This release improves the performance of some methods in Hypothesis's internal
automaton library. These are currently only lightly used by user code, but
this may result in slightly faster shrinking.

.. _v5.26.0:

-------------------
5.26.0 - 2020-08-17
-------------------

:func:`~hypothesis.strategies.register_type_strategy` no longer accepts
parametrised user-defined generic types, because the resolution logic
was quite badly broken (:issue:`2537`).

Instead of registering a strategy for e.g. ``MyCollection[int]``, you
should register a *function* for ``MyCollection`` and `inspect the type
parameters within that function <https://stackoverflow.com/q/48572831>`__.

Thanks to Nikita Sobolev for the bug report, design assistance, and
pull request to implement this feature!

.. _v5.25.0:

-------------------
5.25.0 - 2020-08-16
-------------------

Tired of writing tests?  Or new to Hypothesis and not sure where to start?

This release is for you!  With our new :doc:`Ghostwriter functions <ghostwriter>`
and :command:`hypothesis write ...` :ref:`command-line interface <hypothesis-cli>`,
you can stop writing tests entirely... or take the source code Hypothesis
writes for you as a starting point.

This has been in the works for months, from :issue:`2118` to versions
:ref:`5.18.3 <v5.18.3>`, :ref:`5.23.5 <v5.23.5>`, and :ref:`5.23.5 <v5.23.5>` -
particular thanks to the many people who reviewed pull requests or commented on
demos, and to Timothy Crosley's :pypi:`hypothesis-auto` project for inspiration.

.. _v5.24.4:

-------------------
5.24.4 - 2020-08-14
-------------------

This patch adds yet more internal functions to support a new feature
we're working on, like :ref:`version 5.18.3 <v5.18.3>` and
:ref:`version 5.23.6 <v5.23.6>`.  We promise it's worth the wait!

.. _v5.24.3:

-------------------
5.24.3 - 2020-08-13
-------------------

This release fixes a small internal bug in Hypothesis's internal automaton library.
Fortunately this bug was currently impossible to hit in user facing code, so this
has no user visible impact.

.. _v5.24.2:

-------------------
5.24.2 - 2020-08-12
-------------------

This release improves shrink quality by allowing Hypothesis to automatically learn new shrink passes
for difficult to shrink tests.

The automatic learning is not currently accessible in user code (it still needs significant work
on robustness and performance before it is ready for that), but this release includes learned
passes that should improve shrinking quality for tests which use any of the
:func:`~hypothesis.strategies.text`, :func:`~hypothesis.strategies.floats`,
:func:`~hypothesis.strategies.datetimes`, :func:`~hypothesis.strategies.emails`,
and :func:`~hypothesis.strategies.complex_numbers` strategies.

.. _v5.24.1:

-------------------
5.24.1 - 2020-08-12
-------------------

This patch updates some docstrings, without changing runtime behaviour.

.. _v5.24.0:

-------------------
5.24.0 - 2020-08-10
-------------------

The :func:`~hypothesis.strategies.functions` strategy has a new argument
``pure=True``, which ensures that the same return value is generated for
identical calls to the generated function (:issue:`2538`).

Thanks to Zac Hatfield-Dodds and Nikita Sobolev for this feature!

.. _v5.23.12:

--------------------
5.23.12 - 2020-08-10
--------------------

This release removes a number of Hypothesis's internal "shrink passes" - transformations
it makes to a generated test case during shrinking - which appeared to be redundant with
other transformations.

It is unlikely that you will see much impact from this. If you do, it will likely show up
as a change in shrinking performance (probably slower, maybe faster), or possibly in
worse shrunk results. If you encounter the latter, please let us know.

.. _v5.23.11:

--------------------
5.23.11 - 2020-08-04
--------------------

This release fixes a bug in some internal Hypothesis support code. It has no user visible impact.

.. _v5.23.10:

--------------------
5.23.10 - 2020-08-04
--------------------

This release improves the quality of shrunk test cases in some special cases.
Specifically, it should get shrinking unstuck in some scenarios which require
simultaneously changing two parts of the generated test case.

.. _v5.23.9:

-------------------
5.23.9 - 2020-08-03
-------------------

This release improves the performance of some internal support code. It has no user visible impact,
as that code is not currently run during normal Hypothesis operation.

.. _v5.23.8:

-------------------
5.23.8 - 2020-07-31
-------------------

This release adds a heuristic to detect when shrinking has finished despite the fact
that there are many more possible transformations to try. This will be particularly
useful for tests where the minimum failing test case is very large despite there being
many smaller test cases possible, where it is likely to speed up shrinking dramatically.

In some cases it is likely that this will result in worse shrunk test cases. In those
cases rerunning the test will result in further shrinking.

.. _v5.23.7:

-------------------
5.23.7 - 2020-07-29
-------------------

This release makes some performance improvements to shrinking. They should
only be noticeable for tests that are currently particularly slow to shrink.

.. _v5.23.6:

-------------------
5.23.6 - 2020-07-29
-------------------

This patch adds some more internal functions to support a new
feature we're working on, like :ref:`version 5.18.3 <v5.18.3>`.
There is still no user-visible change... yet.

.. _v5.23.5:

-------------------
5.23.5 - 2020-07-29
-------------------

This release makes some changes to internal support code that is not currently used in production Hypothesis.
It has no user visible effect at present.

.. _v5.23.4:

-------------------
5.23.4 - 2020-07-29
-------------------

This release improves shrinking quality in some special cases.

.. _v5.23.3:

-------------------
5.23.3 - 2020-07-27
-------------------

This release fixes :issue:`2507`, where lazy evaluation meant that the
values drawn from a :func:`~hypothesis.strategies.sampled_from` strategy
could depend on mutations of the sampled sequence that happened after
the strategy was constructed.

.. _v5.23.2:

-------------------
5.23.2 - 2020-07-27
-------------------

This patch fixes :issue:`2462`, a bug in our handling of :meth:`unittest.TestCase.subTest`.
Thanks to Israel Fruchter for fixing this at the EuroPython sprints!

.. _v5.23.1:

-------------------
5.23.1 - 2020-07-26
-------------------

This release improves the behaviour of the :func:`~hypothesis.strategies.characters` strategy
when shrinking, by changing which characters are considered smallest to prefer more "normal" ascii characters
where available.

.. _v5.23.0:

-------------------
5.23.0 - 2020-07-26
-------------------

The default ``print_blob`` setting is now smarter. It defaults to ``True`` in CI and
``False`` for local development.

Thanks to Hugo van Kemenade for implementing this feature at the EuroPython sprints!

.. _v5.22.0:

-------------------
5.22.0 - 2020-07-25
-------------------

The :func:`~hypothesis.strategies.slices` strategy can now generate slices for empty sequences,
slices with negative start and stop indices (from the end of the sequence),
and ``step=None`` in place of ``step=1``.

Thanks to Sangarshanan for implementing this feature at the EuroPython sprints!

.. _v5.21.0:

-------------------
5.21.0 - 2020-07-23
-------------------

This release ensures that tests which raise ``RecursionError`` are not
reported as flaky simply because we run them from different initial
stack depths (:issue:`2494`).

.. _v5.20.4:

-------------------
5.20.4 - 2020-07-23
-------------------

This release improves the performance of the ``sample`` method on objects obtained from :func:`~hypothesis.strategies.randoms`
when ``use_true_random=False``. This should mostly only be noticeable when the sample size is a large fraction of the population size,
but may also help avoid health check failures in some other cases.

.. _v5.20.3:

-------------------
5.20.3 - 2020-07-21
-------------------

This release makes some internal changes for testing purposes and should have no user visible effect.

.. _v5.20.2:

-------------------
5.20.2 - 2020-07-18
-------------------

This release fixes a small caching bug in Hypothesis internals that may under
some circumstances have resulted in a less diverse set of test cases being
generated than was intended.

Fixing this problem revealed some performance problems that could occur during targeted property based testing, so this release also fixes those. Targeted property-based testing should now be significantly faster in some cases,
but this may be at the cost of reduced effectiveness.

.. _v5.20.1:

-------------------
5.20.1 - 2020-07-17
-------------------

This patch updates our formatting to use :pypi:`isort` 5.
There is no user-visible change.

.. _v5.20.0:

-------------------
5.20.0 - 2020-07-17
-------------------

The :func:`~hypothesis.extra.numpy.basic_indices` strategy can now generate
bare indexers in place of length-one tuples. Thanks to Andrea for this patch!

.. _v5.19.3:

-------------------
5.19.3 - 2020-07-15
-------------------

This patch removes an internal use of ``distutils`` in order to avoid
`this setuptools warning <https://github.com/pypa/setuptools/issues/2261>`__
for some users.

.. _v5.19.2:

-------------------
5.19.2 - 2020-07-13
-------------------

This patch contains a small internal refactoring with no user-visible impact.

Thanks to Andrea for writing this at
`the SciPy 2020 Sprints <https://www.scipy2020.scipy.org/sprints-schedule>`__!

.. _v5.19.1:

-------------------
5.19.1 - 2020-07-12
-------------------

This release slightly improves shrinking behaviour. This should mainly only
impact stateful tests, but may have some minor positive impact on shrinking
collections (lists, sets, etc).

.. _v5.19.0:

-------------------
5.19.0 - 2020-06-30
-------------------

This release improves the :func:`~hypothesis.strategies.randoms` strategy by adding support
for ``Random`` instances where Hypothesis generates the random values
rather than having them be "truly" random.

.. _v5.18.3:

-------------------
5.18.3 - 2020-06-27
-------------------

This patch adds some internal functions to support a new feature
we're working on.  There is no user-visible change... yet.

.. _v5.18.2:

-------------------
5.18.2 - 2020-06-26
-------------------

This patch improves our docs for the :obj:`~hypothesis.settings.derandomize` setting.

.. _v5.18.1:

-------------------
5.18.1 - 2020-06-25
-------------------

This release consists of some internal refactoring to the shrinker in preparation for future work. It has no user visible impact.

.. _v5.18.0:

-------------------
5.18.0 - 2020-06-22
-------------------

This release teaches Hypothesis to :ref:`shorten tracebacks <v3.79.2>` for
:ref:`explicit examples <providing-explicit-examples>`, as we already do
for generated examples, so that you can focus on your code rather than ours.

If you have multiple failing explicit examples, they will now all be reported.
To report only the first failure, you can use the :obj:`report_multiple_bugs=False
<hypothesis.settings.report_multiple_bugs>` setting as for generated examples.

.. _v5.17.0:

-------------------
5.17.0 - 2020-06-22
-------------------

This patch adds strategy inference for the ``Literal``, ``NewType``, ``Type``,
``DefaultDict``, and ``TypedDict`` types from the :pypi:`typing-extensions`
backport on PyPI.

.. _v5.16.3:

-------------------
5.16.3 - 2020-06-21
-------------------

This patch precomputes some of the setup logic for our
:ref:`external fuzzer integration <fuzz_one_input>` and sets
:obj:`deadline=None <hypothesis.settings.deadline>` in fuzzing mode,
saving around 150us on each iteration.

This is around two-thirds the runtime to fuzz an empty test with
``@given(st.none())``, and nice to have even as a much smaller
fraction of the runtime for non-trivial tests.

.. _v5.16.2:

-------------------
5.16.2 - 2020-06-19
-------------------

This patch fixes an internal error when warning about the use of function-scoped fixtures
for parametrised tests where the parametrised value contained a ``%`` character.
Thanks to Bryant for reporting and fixing this bug!

.. _v5.16.1:

-------------------
5.16.1 - 2020-06-10
-------------------

If you pass a :class:`python:list` or :class:`python:tuple` where a
strategy was expected, the error message now mentions
:func:`~hypothesis.strategies.sampled_from` as an example strategy.

Thanks to the enthusiastic participants in the `PyCon Mentored Sprints
<https://us.pycon.org/2020/hatchery/mentoredsprints/>`__ who suggested
adding this hint.

.. _v5.16.0:

-------------------
5.16.0 - 2020-05-27
-------------------

:func:`~hypothesis.strategies.functions` can now infer the appropriate ``returns``
strategy if you pass a ``like`` function with a return-type annotation.  Before,
omitting the ``returns`` argument would generate functions that always returned None.

.. _v5.15.1:

-------------------
5.15.1 - 2020-05-21
-------------------

Fix :func:`~hypothesis.strategies.from_type` with generic types under Python 3.9.

.. _v5.15.0:

-------------------
5.15.0 - 2020-05-19
-------------------

This patch fixes an error that happens when multiple threads create new strategies.

.. _v5.14.0:

-------------------
5.14.0 - 2020-05-13
-------------------

Passing ``min_magnitude=None`` to :func:`~hypothesis.strategies.complex_numbers` is now
deprecated - you can explicitly pass ``min_magnitude=0``, or omit the argument entirely.

.. _v5.13.1:

-------------------
5.13.1 - 2020-05-13
-------------------

This patch fixes an internal error in :func:`~hypothesis.strategies.from_type`
for :class:`python:typing.NamedTuple` in Python 3.9.  Thanks to Michel Salim
for reporting and fixing :issue:`2427`!

.. _v5.13.0:

-------------------
5.13.0 - 2020-05-12
-------------------

This release upgrades the test statistics available via the
:ref:`--hypothesis-show-statistics <statistics>` option to include
separate information on each of the :attr:`~hypothesis.settings.phases`
(:issue:`1555`).

.. _v5.12.2:

-------------------
5.12.2 - 2020-05-12
-------------------

This patch teaches the :func:`~hypothesis.strategies.from_type` internals to
return slightly more efficient strategies for some generic sets and mappings.

.. _v5.12.1:

-------------------
5.12.1 - 2020-05-12
-------------------

This patch adds a ``# noqa`` comment for :pypi:`flake8` 3.8.0, which
disagrees with :pypi:`mypy` about how to write the type of ``...``.

.. _v5.12.0:

-------------------
5.12.0 - 2020-05-10
-------------------

This release limits the maximum duration of the shrinking phase to five minutes,
so that Hypothesis does not appear to hang when making very slow progress
shrinking a failing example (:issue:`2340`).

If one of your tests triggers this logic, we would really appreciate a bug
report to help us improve the shrinker for difficult but realistic workloads.

.. _v5.11.0:

-------------------
5.11.0 - 2020-05-07
-------------------

This release improves the interaction between :func:`~hypothesis.assume`
and the :obj:`@example() <hypothesis.example>` decorator, so that the
following test no longer fails with ``UnsatisfiedAssumption`` (:issue:`2125`):

.. code-block:: python

    @given(value=floats(0, 1))
    @example(value=0.56789)  # used to make the test fail!
    @pytest.mark.parametrize("threshold", [0.5, 1])
    def test_foo(threshold, value):
        assume(value < threshold)
        ...

.. _v5.10.5:

-------------------
5.10.5 - 2020-05-04
-------------------

If you have :pypi:`Django` installed but don't use it, this patch will make
``import hypothesis`` a few hundred milliseconds faster (e.g. 0.704s -> 0.271s).

Thanks to :pypi:`importtime-waterfall` for highlighting this problem and
`Jake Vanderplas <https://twitter.com/jakevdp/status/1130983439862181888>`__ for
the solution - it's impossible to misuse code from a module you haven't imported!

.. _v5.10.4:

-------------------
5.10.4 - 2020-04-24
-------------------

This patch improves the internals of :func:`~hypothesis.strategies.builds` type
inference, to handle recursive forward references in certain dataclasses.
This is useful for e.g. :pypi:`hypothesmith`'s forthcoming :pypi:`LibCST <libcst>` mode.

.. _v5.10.3:

-------------------
5.10.3 - 2020-04-22
-------------------

This release reverses the order in which some operations are tried during shrinking.
This should generally be a slight performance improvement, but most tests are unlikely to notice much difference.

.. _v5.10.2:

-------------------
5.10.2 - 2020-04-22
-------------------

This patch fixes :issue:`2406`, where use of :obj:`pandas:pandas.Timestamp`
objects as bounds for the :func:`~hypothesis.strategies.datetimes` strategy
caused an internal error.  This bug was introduced in :ref:`version 5.8.1 <v5.8.2>`.

.. _v5.10.1:

-------------------
5.10.1 - 2020-04-19
-------------------

This release is a small internal refactoring to how shrinking interacts with :ref:`targeted property-based testing <targeted-search>` that should have no user user visible impact.

.. _v5.10.0:

-------------------
5.10.0 - 2020-04-18
-------------------

This release improves our support for datetimes and times around DST transitions.

:func:`~hypothesis.strategies.times` and :func:`~hypothesis.strategies.datetimes`
are now sometimes generated with ``fold=1``, indicating that they represent the
second occurrence of a given wall-time when clocks are set backwards.
This may be set even when there is no transition, in which case the ``fold``
value should be ignored.

For consistency, timezones provided by the :pypi:`pytz` package can now
generate imaginary times (such as the hour skipped over when clocks 'spring forward'
to daylight saving time, or during some historical timezone transitions).
All other timezones have always supported generation of imaginary times.

If you prefer the previous behaviour, :func:`~hypothesis.strategies.datetimes`
now takes an argument ``allow_imaginary`` which defaults to ``True`` but
can be set to ``False`` for any timezones strategy.

.. _v5.9.1:

------------------
5.9.1 - 2020-04-16
------------------

This patch fixes the rendering of :func:`~hypothesis.strategies.binary`
docstring by using the proper backticks syntax.

.. _v5.9.0:

------------------
5.9.0 - 2020-04-15
------------------

Failing tests which use :func:`~hypothesis.target` now report the highest
score observed for each target alongside the failing example(s), even without
:ref:`explicitly showing test statistics <statistics>`.

This improves the debugging workflow for tests of accuracy, which assert that the
total imprecision is within some error budget - for example, ``abs(a - b) < 0.5``.
Previously, shrinking to a minimal failing example could often make errors seem
smaller or more subtle than they really are (see `the threshold problem
<https://hypothesis.works/articles/threshold-problem/>`__, and :issue:`2180`).

.. _v5.8.6:

------------------
5.8.6 - 2020-04-15
------------------

This patch improves the docstring of :func:`~hypothesis.strategies.binary`,
the :func:`python:repr` of :func:`~hypothesis.strategies.sampled_from` on
an :class:`python:enum.Enum` subclass, and a warning in our pytest plugin.
There is no change in runtime behaviour.

.. _v5.8.5:

------------------
5.8.5 - 2020-04-15
------------------

This release (potentially very significantly) improves the performance of failing tests in some rare cases,
mostly only relevant when using :ref:`targeted property-based testing <targeted-search>`,
by stopping further optimisation of unrelated test cases once a failing example is found.

.. _v5.8.4:

------------------
5.8.4 - 2020-04-14
------------------

This release fixes :issue:`2395`, where under some circumstances targeted property-based testing could cause Hypothesis to get caught in an infinite loop.

.. _v5.8.3:

------------------
5.8.3 - 2020-04-12
------------------

This patch teaches :func:`~hypothesis.strategies.builds` and
:func:`~hypothesis.strategies.from_type` to use the ``__signature__``
attribute of classes where it has been set, improving our support
for :pypi:`pydantic` models (`in pydantic >= 1.5
<https://github.com/pydantic/pydantic/pull/1034>`__).

.. _v5.8.2:

------------------
5.8.2 - 2020-04-12
------------------

This release improves the performance of the part of the core engine that
deliberately generates duplicate values.

.. _v5.8.1:

------------------
5.8.1 - 2020-04-12
------------------

This patch improves :func:`~hypothesis.strategies.dates` shrinking, to simplify
year, month, and day like :func:`~hypothesis.strategies.datetimes` rather than
minimizing the number of days since 2000-01-01.

.. _v5.8.0:

------------------
5.8.0 - 2020-03-24
------------------

This release adds a :ref:`.hypothesis.fuzz_one_input <fuzz_one_input>`
attribute to :func:`@given <hypothesis.given>` tests, for easy integration
with external fuzzers such as `python-afl <https://github.com/jwilk/python-afl>`__
(supporting :issue:`171`).

.. _v5.7.2:

------------------
5.7.2 - 2020-03-24
------------------

This patch fixes :issue:`2341`, ensuring that the printed output from a
stateful test cannot use variable names before they are defined.

.. _v5.7.1:

------------------
5.7.1 - 2020-03-23
------------------

This patch fixes :issue:`2375`, preventing incorrect failure when a function
scoped fixture is overridden with a higher scoped fixture.

.. _v5.7.0:

------------------
5.7.0 - 2020-03-19
------------------

This release allows the :func:`~hypothesis.extra.numpy.array_dtypes` strategy
to generate Numpy dtypes which have `field titles in addition to field names
<https://numpy.org/doc/stable/user/basics.rec.html#field-titles>`__.
We expect this to expose latent bugs where code expects that
``set(dtype.names) == set(dtype.fields)``, though the latter may include titles.

.. _v5.6.1:

------------------
5.6.1 - 2020-03-18
------------------

This makes ``model`` a positional-only argument to
:func:`~hypothesis.extra.django.from_model`, to support models
with a field literally named "model" (:issue:`2369`).

.. _v5.6.0:

------------------
5.6.0 - 2020-02-29
------------------

This release adds an explicit warning for tests that are both decorated with
:func:`@given(...) <hypothesis.given>` and request a
:doc:`function-scoped pytest fixture <pytest:how-to/fixtures>`, because such fixtures
are only executed once for *all* Hypothesis test cases and that often causes
trouble (:issue:`377`).

It's *very* difficult to fix this on the :pypi:`pytest` side, so since 2015
our advice has been "just don't use function-scoped fixtures with Hypothesis".
Now we detect and warn about the issue at runtime!

.. _v5.5.5:

------------------
5.5.5 - 2020-02-29
------------------

This release cleans up the internal machinery for :doc:`stateful`,
after we dropped the legacy APIs in Hypothesis 5.0 (:issue:`2218`).
There is no user-visible change.

.. _v5.5.4:

------------------
5.5.4 - 2020-02-16
------------------

This patch fixes :issue:`2351`, :func:`~hypothesis.extra.numpy.arrays` would
raise a confusing error if we inferred a strategy for ``datetime64`` or
``timedelta64`` values with varying time units.

We now infer an internally-consistent strategy for such arrays, and have a more
helpful error message if an inconsistent strategy is explicitly specified.

.. _v5.5.3:

------------------
5.5.3 - 2020-02-14
------------------

This patch improves the signature of :func:`~hypothesis.strategies.builds` by
specifying ``target`` as a positional-only argument on Python 3.8 (see :pep:`570`).
The semantics of :func:`~hypothesis.strategies.builds` have not changed at all -
this just clarifies the documentation.

.. _v5.5.2:

------------------
5.5.2 - 2020-02-13
------------------

This release makes Hypothesis faster at generating test cases that contain
duplicated values in their inputs.

.. _v5.5.1:

------------------
5.5.1 - 2020-02-07
------------------

This patch has some tiny internal code clean-ups, with no user-visible change.

.. _v5.5.0:

------------------
5.5.0 - 2020-02-07
------------------

:gh-file:`Our style guide <guides/api-style.rst>` suggests that optional
parameters should usually be keyword-only arguments (see :pep:`3102`) to
prevent confusion based on positional arguments - for example,
:func:`hypothesis.strategies.floats` takes up to *four* boolean flags
and many of the Numpy strategies have both ``dims`` and ``side`` bounds.

This release converts most optional parameters in our API to use
keyword-only arguments - and adds a compatibility shim so you get
warnings rather than errors everywhere (:issue:`2130`).

.. _v5.4.2:

------------------
5.4.2 - 2020-02-06
------------------

This patch fixes compatibility with Python 3.5.2 (:issue:`2334`).
Note that :doc:`we only test the latest patch of each minor version <supported>`,
though as in this case we usually accept pull requests for older patch versions.

.. _v5.4.1:

------------------
5.4.1 - 2020-02-01
------------------

This patch improves the repr of :func:`~hypothesis.strategies.from_type`,
so that in most cases it will display the strategy it resolves to rather
than ``from_type(...)``.  The latter form will continue to be used where
resolution is not immediately successful, e.g. invalid arguments or
recursive type definitions involving forward references.

.. _v5.4.0:

------------------
5.4.0 - 2020-01-30
------------------

This release removes support for Python 3.5.0 and 3.5.1, where the
:mod:`python:typing` module was quite immature (e.g. missing
:func:`~python:typing.overload` and :obj:`~python:typing.Type`).

Note that Python 3.5 will reach its end-of-life in September 2020,
and new releases of Hypothesis may drop support somewhat earlier.

.. note::
    ``pip install hypothesis`` should continue to give you the latest compatible version.
    If you have somehow ended up with an incompatible version, you need to update your
    packaging stack to ``pip >= 9.0`` and ``setuptools >= 24.2`` - see `here for details
    <https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires>`__.
    Then ``pip uninstall hypothesis && pip install hypothesis`` will get you back to
    a compatible version.

.. _v5.3.1:

------------------
5.3.1 - 2020-01-26
------------------

This patch does some minor internal cleanup; there is no user-visible change.

.. _v5.3.0:

------------------
5.3.0 - 2020-01-21
------------------

The standard library :mod:`ipaddress` module is new in Python 3, and this release
adds the new :func:`~hypothesis.strategies.ip_addresses` strategy to generate
:class:`~python:ipaddress.IPv4Address`\ es and/or
:class:`~python:ipaddress.IPv6Address`\ es (depending on the ``v`` and ``network``
arguments).

If you use them in type annotations, :func:`~hypothesis.strategies.from_type` now
has strategies registered for :mod:`ipaddress` address, network, and interface types.

The provisional strategies for IP address strings are therefore deprecated.

.. _v5.2.1:

------------------
5.2.1 - 2020-01-21
------------------

This patch reverts :ref:`version 5.2 <v5.2.0>`, due to a
`strange issue <https://github.com/numpy/numpy/issues/15363>`__
where indexing an array of strings can raise an error instead of
returning an item which contains certain surrogate characters.

.. _v5.2.0:

------------------
5.2.0 - 2020-01-19
------------------

This release allows :func:`~hypothesis.extra.numpy.from_dtype` to generate
Unicode strings which cannot be encoded in UTF-8, but are valid in Numpy
arrays (which use UTF-32).

.. _v5.1.6:

------------------
5.1.6 - 2020-01-19
------------------

This patch fixes :issue:`2320`, where ``from_type(Set[Hashable])`` could raise
an internal error because ``Decimal("snan")`` is of a hashable type, but raises
an error when hashed.  We now ensure that set elements and dict keys in generic
types can actually be hashed.

.. _v5.1.5:

------------------
5.1.5 - 2020-01-12
------------------

This patch fixes an internal error when running in an :pypi:`ipython` repl or
:pypi:`jupyter` notebook on Windows (:issue:`2319`), and an internal error on
Python 3.5.1 (:issue:`2318`).

.. _v5.1.4:

------------------
5.1.4 - 2020-01-11
------------------

This patch fixes a bug where errors in third-party extensions such as
:pypi:`hypothesis-trio` or :pypi:`hypothesis-jsonschema` were incorrectly
considered to be Hypothesis internal errors, which could result in
confusing error messages.

Thanks to Vincent Michel for reporting and fixing the bug!

.. _v5.1.3:

------------------
5.1.3 - 2020-01-11
------------------

This release converts the type hint comments on our public API to
:pep:`484` type annotations.

Thanks to Ivan Levkivskyi for :pypi:`com2ann` - with the refactoring
tools from :ref:`5.0.1 <v5.0.1>` it made this process remarkably easy!

.. _v5.1.2:

------------------
5.1.2 - 2020-01-09
------------------

This patch makes :func:`~hypothesis.stateful.multiple` iterable, so that
output like ``a, b = state.some_rule()`` is actually executable and
can be used to reproduce failing examples.

Thanks to Vincent Michel for reporting and fixing :issue:`2311`!

.. _v5.1.1:

------------------
5.1.1 - 2020-01-06
------------------

This patch contains many small refactorings to replace our Python 2
compatibility functions with their native Python 3 equivalents.
Since Hypothesis is now Python 3 only, there is no user-visible change.

.. _v5.1.0:

------------------
5.1.0 - 2020-01-03
------------------

This release teaches :func:`~hypothesis.strategies.from_type` how to generate
:class:`python:datetime.timezone`.  As a result, you can now generate
:class:`python:datetime.tzinfo` objects without having :pypi:`pytz` installed.

If your tests specifically require :pypi:`pytz` timezones, you should be using
:func:`hypothesis.extra.pytz.timezones` instead of ``st.from_type(tzinfo)``.

.. _v5.0.1:

------------------
5.0.1 - 2020-01-01
------------------

This patch contains mostly-automated refactorings to remove code
that we only needed to support Python 2.  Since Hypothesis is now
Python 3 only (hurray!), there is no user-visible change.

Our sincere thanks to the authors of :pypi:`autoflake`, :pypi:`black`,
:pypi:`isort`, and :pypi:`pyupgrade`, who have each and collectively
made this kind of update enormously easier.

.. _v5.0.0:

------------------
5.0.0 - 2020-01-01
------------------

Welcome to the next major version of Hypothesis!

There are no new features here, as we release those in minor versions.
Instead, 5.0 is a chance for us to remove deprecated features (many already
converted into no-ops), and turn a variety of warnings into errors.

If you were running on the last version of Hypothesis 4.x *without any
Hypothesis deprecation warnings*, this will be a very boring upgrade.
**In fact, nothing will change for you at all.**

.. note::
    This release drops support for Python 2, which has passed
    `its end of life date <https://devguide.python.org/#status-of-python-branches>`__.
    The `Python 3 Statement <https://python3statement.github.io>`__ outlines our
    reasons, and lists many other packages that have made the same decision.

    ``pip install hypothesis`` should continue to give you the latest compatible version.
    If you have somehow ended up with Hypothesis 5.0 on Python 2, you need to update your
    packaging stack to ``pip >= 9.0`` and ``setuptools >= 24.2`` - see `here for details
    <https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires>`__.
    Then ``pip uninstall hypothesis && pip install hypothesis`` will get you back to
    a compatible version.


Strategies
~~~~~~~~~~
- :func:`~hypothesis.strategies.integers` bounds must be equal to an integer,
  though they can still be other types.
- If :func:`~hypothesis.strategies.fractions` is passed a ``max_denominator``,
  the bounds must have at most that denominator.
- :func:`~hypothesis.strategies.floats` bounds must be exactly representable as a
  floating-point number with the given ``width``.  If not, the error message
  includes the nearest such number.
- :func:`sampled_from([]) <hypothesis.strategies.sampled_from>` is now an error.
- The values from the ``elements`` and ``fill`` strategies for
  :func:`hypothesis.extra.numpy.arrays` must be losslessly representable in an
  array of the given dtype.
- The ``min_size`` and ``max_size`` arguments to all collection strategies must
  be of type :class:`python:int` (or ``max_size`` may be ``None``).

Miscellaneous
~~~~~~~~~~~~~
- The ``.example()`` method of strategies (intended for interactive
  exploration) no longer takes a ``random`` argument.
- It is now an error to apply :obj:`@example <hypothesis.example>`,
  :func:`@seed <hypothesis.seed>`, or :func:`@reproduce_failure <hypothesis.reproduce_failure>`
  without also applying :func:`@given <hypothesis.given>`.
- You may pass either the ``target`` or ``targets`` argument to stateful rules, but not both.
- :obj:`~hypothesis.settings.deadline` must be ``None`` (to disable), a
  :class:`~python:datetime.timedelta`, or an integer or float number of milliseconds.
- Both of :obj:`~hypothesis.settings.derandomize` and
  :obj:`~hypothesis.settings.print_blob` must be either ``True`` or ``False``,
  where they previously accepted other values.
- :obj:`~hypothesis.settings.stateful_step_count` must be at least one.
- :obj:`~hypothesis.settings.max_examples` must be at least one.
  To disable example generation, use the :obj:`~hypothesis.settings.phases` setting.

Removals
~~~~~~~~
- ``hypothesis.stateful.GenericStateMachine`` in favor of :class:`hypothesis.stateful.RuleBasedStateMachine`
- ``hypothesis.extra.django.models.models`` in favor of :func:`hypothesis.extra.django.from_model`
  and ``hypothesis.extra.django.models.add_default_field_mapping`` in favor of
  :func:`hypothesis.extra.django.register_field_strategy`
- ``hypothesis.HealthCheck.hung_test``, without replacement
- ``hypothesis.settings.buffer``, without replacement
- ``hypothesis.PrintSettings``, because :obj:`hypothesis.settings.print_blob` takes ``True`` or ``False``
- ``hypothesis.settings.timeout``, in favor of :obj:`hypothesis.settings.deadline`
- ``hypothesis.unlimited`` without replacement (only only useful as argument to ``timeout``)

Hypothesis 4.x
==============

.. _v4.57.1:

-------------------
4.57.1 - 2019-12-29
-------------------

This patch improves the type hints and documentation for the
:doc:`django extra. <django>`  There is no runtime change.

.. _v4.57.0:

-------------------
4.57.0 - 2019-12-28
-------------------

This release improves support for the SupportsOp protocols from the :mod:`python:typing`
module when using on :func:`~hypothesis.strategies.from_type` as outlined in :issue:`2292`.
The following types now generate much more varied strategies when called
with :func:`~hypothesis.strategies.from_type`:

- :class:`python:typing.SupportsAbs`
- :class:`python:typing.SupportsBytes`
- :class:`python:typing.SupportsComplex`
- :class:`python:typing.SupportsInt`
- :class:`python:typing.SupportsFloat`
- :class:`python:typing.SupportsRound`

Note that using :func:`~hypothesis.strategies.from_type` with one of the above strategies will not
ensure that the the specified function will execute successfully (ie : the strategy returned for
``from_type(typing.SupportsAbs)`` may include NaNs or things which cause the :func:`python:abs`
function to error. )

Thanks to Lea Provenzano for this patch.

.. _v4.56.3:

-------------------
4.56.3 - 2019-12-22
-------------------

This release fixes a small internal bug in shrinking which could have caused it
to perform slightly more tests than were necessary. Fixing this shouldn't have
much effect but it will make shrinking slightly faster.

.. _v4.56.2:

-------------------
4.56.2 - 2019-12-21
-------------------

This release removes an internal heuristic that was no longer providing much
benefit. It is unlikely that there will be any user visible effect.

.. _v4.56.1:

-------------------
4.56.1 - 2019-12-19
-------------------

This release further improves the optimisation algorithm for :ref:`targeted property-based testing <targeted-search>`.

.. _v4.56.0:

-------------------
4.56.0 - 2019-12-18
-------------------

This release enables deprecation warnings even when the
:obj:`~hypothesis.settings.verbosity` setting is ``quiet``,
in preparation for Hypothesis 5.0 (:issue:`2218`).

Warnings can still be filtered by the standard mechanisms
provided in the standard-library :mod:`python:warnings` module.

.. _v4.55.4:

-------------------
4.55.4 - 2019-12-18
-------------------

This release improves Hypothesis's management of the set of test cases it
tracks between runs. It will only do anything if you have the
:obj:`~hypothesis.Phase.target` phase enabled and an example database set.
In those circumstances it should result in a more thorough and faster set of examples
that are tried on each run.

.. _v4.55.3:

-------------------
4.55.3 - 2019-12-18
-------------------

This release makes Hypothesis better at generating test cases where generated
values are duplicated in different parts of the test case. This will be
especially noticeable with reasonably complex values, as it was already able
to do this for simpler ones such as integers or floats.

.. _v4.55.2:

-------------------
4.55.2 - 2019-12-17
-------------------

This release expands the set of test cases that Hypothesis saves in its
database for future runs to include a representative set of "structurally
different" test cases - e.g. it might try to save test cases where a given list
is empty or not.

Currently this is unlikely to have much user visible impact except to produce
slightly more consistent behaviour between consecutive runs of a test suite.
It is mostly groundwork for future improvements which will exploit this
functionality more effectively.

.. _v4.55.1:

-------------------
4.55.1 - 2019-12-16
-------------------

This patch fixes :issue:`2257`, where :func:`~hypothesis.strategies.from_type`
could incorrectly generate bytestrings when passed a generic
:class:`python:typing.Sequence` such as ``Sequence[set]``.

.. _v4.55.0:

-------------------
4.55.0 - 2019-12-16
-------------------

This release adds database support for :ref:`targeted property-based testing <targeted-search>`,
so the best examples based on the targeting will be saved and reused between runs.
This is mostly laying groundwork for future features in this area, but
will also make targeted property-based tests more useful during development,
where the same tests tend to get run over and over again.

If :obj:`~hypothesis.settings.max_examples` is large, this may increase memory
usage significantly under some circumstances, but these should be relatively
rare.

This release also adds a dependency on the :pypi:`sortedcontainers` package.

.. _v4.54.2:

-------------------
4.54.2 - 2019-12-16
-------------------

This release improves the optimisation algorithm for :ref:`targeted property-based testing <targeted-search>`,
so that it will find higher quality results more reliably. Specifically, in cases where it would previously have got near a local optimum,
it will now tend to achieve the locally optimal value.

.. _v4.54.1:

-------------------
4.54.1 - 2019-12-16
-------------------

This release is mostly internal changes in support of better testing of the
core engine. You are unlikely to see much effect, although some internal
heuristics have changed slightly.

.. _v4.54.0:

-------------------
4.54.0 - 2019-12-15
-------------------

This release adds a dedicated phase for :ref:`targeted property-based testing <targeted-search>`,
and (somewhat) improves the targeting algorithm so that it will find higher quality results more reliably.
This comes at a cost of making it more likely to get stuck in a local optimum.

.. _v4.53.3:

-------------------
4.53.3 - 2019-12-15
-------------------

This patch fixes :func:`~hypothesis.strategies.from_type` with
:class:`python:typing.Hashable` and :class:`python:typing.Sized`,
which previously failed with an internal error on Python 3.7 or later.

Thanks to Lea Provenzano for both reporting :issue:`2272`
and writing the patch!

.. _v4.53.2:

-------------------
4.53.2 - 2019-12-11
-------------------

This release reorganises a number of the Hypothesis internal modules into a
package structure. If you are only depending on the public API it should have
no effect. If you are depending on the internal API (which you shouldn't be,
and which we don't guarantee compatibility on) you may have to rename some
imports.

.. _v4.53.1:

-------------------
4.53.1 - 2019-12-09
-------------------

This release changes the size distribution of the number of steps run in
stateful testing: It will now almost always run the maximum number of steps
permitted.

.. _v4.53.0:

-------------------
4.53.0 - 2019-12-09
-------------------

:ref:`statistics` now include the best score seen for each label, which can help avoid
`the threshold problem <https://hypothesis.works/articles/threshold-problem/>`__  when
the minimal example shrinks right down to the threshold of failure (:issue:`2180`).

.. _v4.52.0:

-------------------
4.52.0 - 2019-12-09
-------------------

This release changes the ``stateful_step_count`` setting to raise an error if
set to ``0``. This is a backwards compatible change because a value of ``0``
would never have worked and attempting to run it would have resulted in an
internal assertion error.

.. _v4.51.1:

-------------------
4.51.1 - 2019-12-09
-------------------

This release makes a small internal change to the distribution of test cases.
It is unlikely to have much user visible impact.

.. _v4.51.0:

-------------------
4.51.0 - 2019-12-07
-------------------

This release deprecates use of :obj:`@example <hypothesis.example>`,
:func:`@seed <hypothesis.seed>`, or :func:`@reproduce_failure <hypothesis.reproduce_failure>`
without :func:`@given <hypothesis.given>`.

Thanks to Nick Anyos for the patch!

.. _v4.50.8:

-------------------
4.50.8 - 2019-12-05
-------------------

This patch makes certain uses of Bundles more efficient in stateful testing (:issue:`2078`).

.. _v4.50.7:

-------------------
4.50.7 - 2019-12-05
-------------------

This release refactors some of Hypothesis's internal interfaces for representing
data generation. It should have no user visible effect.

.. _v4.50.6:

-------------------
4.50.6 - 2019-12-02
-------------------

This patch removes some old debugging helpers in our Numpy extra which have
not been needed since :issue:`1963` and :issue:`2245`.

.. _v4.50.5:

-------------------
4.50.5 - 2019-12-01
-------------------

This patch fixes :issue:`2229`, where Numpy arrays of unsized strings would
only ever have strings of size one due to an interaction between our generation
logic and Numpy's allocation strategy.

.. _v4.50.4:

-------------------
4.50.4 - 2019-12-01
-------------------

This patch fixes a rare internal error in strategies for a list of
unique items sampled from a short non-unique sequence (:issue:`2247`).
The bug was discovered via :pypi:`hypothesis-jsonschema`.

.. _v4.50.3:

-------------------
4.50.3 - 2019-12-01
-------------------

This release improves the error message when
:func:`@settings <hypothesis.settings>` tries to inherit settings from a
``parent`` argument that isn't a ``settings`` instance.

.. _v4.50.2:

-------------------
4.50.2 - 2019-11-29
-------------------

This release improves Hypothesis's "Falsifying example" output, by breaking
output across multiple lines where necessary, and by removing irrelevant
information from the stateful testing output.

.. _v4.50.1:

-------------------
4.50.1 - 2019-11-29
-------------------

This patch adds :pypi:`flake8-comprehensions` to our linter suite.  There is no
user-visible change - expect perhaps via some strange microbenchmarks - but
certain parts of the code now have a clear and more consistent style.

.. _v4.50.0:

-------------------
4.50.0 - 2019-11-28
-------------------

This release fixes some cases where we might previously have failed to run the
validation logic for some strategies. As a result tests which would previously
have been silently testing significantly less than they should may now start
to raise ``InvalidArgument`` now that these errors are caught.

.. _v4.49.0:

-------------------
4.49.0 - 2019-11-28
-------------------

This release significantly improves the data distribution in :doc:`rule based stateful testing <stateful>`,
by using a technique called `Swarm Testing (Groce, Alex, et al. "Swarm testing."
Proceedings of the 2012 International Symposium on Software Testing and Analysis. ACM, 2012.) <https://agroce.github.io/issta12.pdf>`_
to select which rules are run in any given test case. This should allow it to find many issues that it would previously have missed.

This change is likely to be especially beneficial for stateful tests with large numbers of rules.

.. _v4.48.1:

-------------------
4.48.1 - 2019-11-28
-------------------

This release adds some heuristics to test case generation that try to ensure that test cases generated early on will be relatively small.

This fixes a bug introduced in :ref:`Hypothesis 4.42.0 <v4.42.0>` which would cause occasional
:obj:`~hypothesis.HealthCheck.too_slow` failures on some tests.

.. _v4.48.0:

-------------------
4.48.0 - 2019-11-28
-------------------

This release revokes the deprecation of ``find``, as we've now rebuilt it on top of
``@given``, which means it has minimal maintenance burden and we're happy to support it.

.. _v4.47.5:

-------------------
4.47.5 - 2019-11-28
-------------------

This release rebuilds ``find()`` on top of ``@given`` in order to have more code in common.
It should have minimal user visible effect.

.. _v4.47.4:

-------------------
4.47.4 - 2019-11-27
-------------------

This patch removes an internal compatibility shim that we no longer need.

.. _v4.47.3:

-------------------
4.47.3 - 2019-11-26
-------------------

This patch fixes several typos in our docstrings and comments,
with no change in behaviour.  Thanks to  Dmitry Dygalo for
identifying and fixing them!

.. _v4.47.2:

-------------------
4.47.2 - 2019-11-25
-------------------

This release fixes an internal issue where Hypothesis would sometimes generate
test cases that were above its intended maximum size. This would only have
happened rarely and probably would not have caused major problems when it did.

Users of the new  :ref:`targeted property-based testing <targeted-search>` might
see minor impact (possibly slightly faster tests and slightly worse target scores),
but only in the unlikely event that they were hitting this problem. Other users
should not see any effect at all.

.. _v4.47.1:

-------------------
4.47.1 - 2019-11-24
-------------------

This release removes some unused code from the core engine.
There is no user-visible change.

.. _v4.47.0:

-------------------
4.47.0 - 2019-11-24
-------------------

This release commonizes some code between running explicit examples and normal test execution.
The main user visible impact of this is that deadlines are now enforced when running explicit examples.

.. _v4.46.1:

-------------------
4.46.1 - 2019-11-23
-------------------

This patch ensures that a KeyboardInterrupt received during example generation
is not treated as a mystery test failure but instead propagates to the top
level, not recording the interrupted generation in the conjecture data tree.
Thanks to Anne Archibald for identifying and fixing the problem.

.. _v4.46.0:

-------------------
4.46.0 - 2019-11-22
-------------------

This release changes the behaviour of :func:`~hypothesis.strategies.floats`
when excluding signed zeros - ``floats(max_value=0.0, exclude_max=True)``
can no longer generate ``-0.0`` nor the much rarer
``floats(min_value=-0.0, exclude_min=True)`` generate ``+0.0``.

The correct interaction between signed zeros and exclusive endpoints was unclear;
we now enforce the invariant that :func:`~hypothesis.strategies.floats` will
never generate a value equal to an excluded endpoint (:issue:`2201`).

If you prefer the old behaviour, you can pass ``floats(max_value=-0.0)`` or
``floats(min_value=0.0)`` which is exactly equivalent and has not changed.
If you had *two* endpoints equal to zero, we recommend clarifying your tests by using
:func:`~hypothesis.strategies.just` or :func:`~hypothesis.strategies.sampled_from`
instead of :func:`~hypothesis.strategies.floats`.

.. _v4.45.1:

-------------------
4.45.1 - 2019-11-20
-------------------

This patch improves the error message when invalid arguments are passed
to :func:`~hypothesis.stateful.rule` or :func:`~hypothesis.stateful.invariant`
(:issue:`2149`).

Thanks to Benjamin Palmer for this bugfix!

.. _v4.45.0:

-------------------
4.45.0 - 2019-11-20
-------------------

This release supports :obj:`python:typing.Final` and :obj:`python:typing.TypedDict`
in :func:`~hypothesis.strategies.from_type`.

.. _v4.44.5:

-------------------
4.44.5 - 2019-11-20
-------------------

This patch disables our :pypi:`pytest` plugin when running on versions
of :pypi:`pytest` before 4.3, the oldest our plugin supports.
Note that at time of writing the Pytest developers only support 4.6 and later!

Hypothesis *tests* using :func:`@given() <hypothesis.given>` work on any
test runner, but our integrations to e.g. avoid example database collisions
when combined with ``@pytest.mark.parametrize`` eventually drop support
for obsolete versions.

.. _v4.44.4:

-------------------
4.44.4 - 2019-11-20
-------------------

This patch adds some internal comments and clarifications to the Hypothesis
implementation. There is no user-visible change.

.. _v4.44.3:

-------------------
4.44.3 - 2019-11-20
-------------------

This patch avoids importing test runners such as :pypi:`pytest`, :pypi:`unittest2`,
or :pypi:`nose` solely to access their special "skip test" exception types -
if the module is not in :obj:`sys.modules`, the exception can't be raised anyway.

This fixes a problem where importing an otherwise unused module could cause
spurious errors due to import-time side effects (and possibly ``-Werror``).

.. _v4.44.2:

-------------------
4.44.2 - 2019-11-12
-------------------

This release fixes :func:`@given <hypothesis.given>` to only complain about
missing keyword-only arguments if the associated test function is actually
called.

This matches the behaviour of other ``InvalidArgument`` errors produced by
``@given``.

.. _v4.44.1:

-------------------
4.44.1 - 2019-11-11
-------------------

This patch allows Hypothesis to run in environments that do not specify
a ``__file__``, such as a :mod:`python:zipapp` (:issue:`2196`).

.. _v4.44.0:

-------------------
4.44.0 - 2019-11-11
-------------------

This release adds a ``signature`` argument to
:func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes` (:issue:`2174`),
which allows us to generate shapes which are valid for functions like
:data:`np.matmul() <numpy:numpy.matmul>` that require shapes which are not simply broadcastable.

Thanks to everyone who has contributed to this feature over the last year,
and a particular shout-out to Zac Hatfield-Dodds and Ryan Soklaski for
:func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes` and to
Ryan Turner for the downstream :pypi:`hypothesis-gufunc` project.

.. _v4.43.9:

-------------------
4.43.9 - 2019-11-11
-------------------

This patch fixes :issue:`2108`, where the first test using
:func:`~hypothesis.strategies.data` to draw from :func:`~hypothesis.strategies.characters`
or :func:`~hypothesis.strategies.text` would be flaky due to unreliable test timings.

Time taken by lazy instantiation of strategies is now counted towards drawing from
the strategy, rather than towards the deadline for the test function.

.. _v4.43.8:

-------------------
4.43.8 - 2019-11-08
-------------------

This release ensures that the strategies passed to
:func:`@given <hypothesis.given>` are properly validated when applied to a test
method inside a test class.

This should result in clearer error messages when some of those strategies are
invalid.

.. _v4.43.7:

-------------------
4.43.7 - 2019-11-08
-------------------

This release changes how Hypothesis manages its search space in cases where it
generates redundant data. This should cause it to generate significantly fewer
duplicated examples (especially with short integer ranges), and may cause it to
produce more useful examples in some cases (especially ones where there is a
significant amount of filtering).

.. _v4.43.6:

-------------------
4.43.6 - 2019-11-07
-------------------

This patch refactors ``width`` handling in :func:`~hypothesis.strategies.floats`;
you may notice small performance improvements but the main purpose is to
enable work on :issue:`1704` (improving shrinking of bounded floats).

.. _v4.43.5:

-------------------
4.43.5 - 2019-11-06
-------------------

This patch removes an unused internal flag.
There is no user-visible change.

.. _v4.43.4:

-------------------
4.43.4 - 2019-11-05
-------------------

This patch corrects the exception type and error message you get if you attempt
to use :func:`~hypothesis.strategies.data` to draw from something which is not
a strategy.  This never worked, but the error is more helpful now.

.. _v4.43.3:

-------------------
4.43.3 - 2019-11-05
-------------------

We've adopted :pypi:`flake8-bugbear` to check for a few more style issues,
and this patch implements the minor internal cleanups it suggested.
There is no user-visible change.

.. _v4.43.2:

-------------------
4.43.2 - 2019-11-05
-------------------

This patch fixes the formatting of some documentation,
but there is no change to any executed code.

.. _v4.43.1:

-------------------
4.43.1 - 2019-11-04
-------------------

Python 3.8's new :obj:`python:typing.Literal` type - see :pep:`586` for
details - is now  supported in :func:`~hypothesis.strategies.from_type`.

.. _v4.43.0:

-------------------
4.43.0 - 2019-11-04
-------------------

This release adds the strategy :func:`~hypothesis.extra.numpy.mutually_broadcastable_shapes`, which generates multiple array shapes that are mutually broadcast-compatible with an optional user-specified base-shape.

This is a generalisation of :func:`~hypothesis.extra.numpy.broadcastable_shapes`.
It relies heavily on non-public internals for performance when generating and shrinking examples.
We intend to support generating shapes matching a ufunc signature in a future version (:issue:`2174`).

Thanks to Ryan Soklaski, Zac Hatfield-Dodds, and @rdturnermtl who contributed to this new feature.

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
`builtin cache plugin <https://docs.pytest.org/en/latest/how-to/cache.html>`__
(:issue:`2155`).

.. _v4.42.7:

-------------------
4.42.7 - 2019-11-02
-------------------

This patch makes stateful step printing expand the result of a step into
multiple variables when you return :func:`~hypothesis.stateful.multiple` (:issue:`2139`).
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

This release updates Hypothesis's formatting to the new version of :pypi:`black`, and
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
to generate `basic indexes <https://numpy.org/doc/stable/user/basics.indexing.html>`__
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
:ref:`targeted property-based testing <targeted-search>`
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

This is very useful for :pypi:`hypothesmith` to support :pypi:`libCST <libcst>`.

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
now interpreted as ``include_characters`` to :func:`~hypothesis.strategies.characters`
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
packages, `will drop Python 2 support on 2020-01-01 <https://python3statement.github.io>`__
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
is now deprecated.  While ``0. == -0.`` and we could thus generate either if
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
modest, but worthwhile for small arrays.

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
zero-dimensional arrays with ``dtype=object`` and a strategy for iterable elements.
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
:wikipedia:`open or half-open intervals <Interval_(mathematics)>`
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


Hypothesis 3.x
==============

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
`~django.db.models.URLField`, thanks to a new provisional strategy for URLs (:issue:`1388`).

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

Hypothesis has adopted :pypi:`black` as our code formatter (:issue:`1686`).
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
uses its default value of ``characters(exclude_categories=('Cs',))``
directly, instead of hiding that behind ``alphabet=None`` and replacing
it within the function.  Passing ``None`` is therefore deprecated.

.. _v3.81.0:

-------------------
3.81.0 - 2018-10-27
-------------------

``GenericStateMachine`` and
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
and ``GenericStateMachine``.

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

Check our :gh-file:`CITATION.cff` file for details, or head right on over to
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
avoid unnecessary work in some cases.

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

This release adds type hints to the :obj:`@example() <hypothesis.example>` and
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
(eg ``'Nd'``), or as the 'major category' (eg ``['N', 'Lu']``
is equivalent to ``['Nd', 'Nl', 'No', 'Lu']``).

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
Profiling suggests this is a 5-10% performance improvement (:issue:`1040`).

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

This release fixes :issue:`1041`, which slowed tests by up to 6%
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
:func:`~hypothesis.strategies.characters` when using ``exclude_characters``
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

This release overhauls :ref:`the health check system <healthchecks>`
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
if passed a :obj:`~typing.NewType` (:issue:`901`).  These pseudo-types
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
an :obj:`@example <hypothesis.example>` would print an extra stack trace before re-raising the
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
``include_characters`` and ``exclude_characters`` to
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
  ``include_characters``, particular characters which will be added to those
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

* The :obj:`~hypothesis.Phase.reuse` phase will now correctly control whether examples
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
:obj:`@example <hypothesis.example>` and a pytest fixture in the same test
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


Older versions
==============

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
