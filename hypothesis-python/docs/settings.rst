========
Settings
========

Hypothesis tries to have good defaults for its behaviour, but sometimes that's
not enough and you need to tweak it.

The mechanism for doing this is the :class:`~hypothesis.settings` object.
You can set up a :func:`@given <hypothesis.given>` based test to use this using a settings
decorator:

:func:`@given <hypothesis.given>` invocation is as follows:

.. code:: python

    from hypothesis import given, settings

    @given(integers())
    @settings(max_examples=500)
    def test_this_thoroughly(x):
        pass

This uses a :class:`~hypothesis.settings` object which causes the test to receive a much larger
set of examples than normal.

This may be applied either before or after the given and the results are
the same. The following is exactly equivalent:


.. code:: python

    from hypothesis import given, settings

    @settings(max_examples=500)
    @given(integers())
    def test_this_thoroughly(x):
        pass

------------------
Available settings
------------------

.. module:: hypothesis
.. autoclass:: settings
    :members: max_examples, max_iterations, min_satisfying_examples,
        max_shrinks, timeout, strict, database_file, stateful_step_count,
        database, perform_health_check, suppress_health_check, buffer_size,
        phases, deadline, use_coverage, derandomize

.. _phases:

~~~~~~~~~~~~~~~~~~~~~
Controlling What Runs
~~~~~~~~~~~~~~~~~~~~~

Hypothesis divides tests into four logically distinct phases:

1. Running explicit examples :ref:`provided with the @example decorator <providing-explicit-examples>`.
2. Rerunning a selection of previously failing examples to reproduce a previously seen error
3. Generating new examples.
4. Attempting to shrink an example found in phases 2 or 3 to a more manageable
   one (explicit examples cannot be shrunk).

The phases setting provides you with fine grained control over which of these run,
with each phase corresponding to a value on the :class:`~hypothesis._settings.Phase` enum:

1. ``Phase.explicit`` controls whether explicit examples are run.
2. ``Phase.reuse`` controls whether previous examples will be reused.
3. ``Phase.generate`` controls whether new examples will be generated.
4. ``Phase.shrink`` controls whether examples will be shrunk.

The phases argument accepts a collection with any subset of these. e.g.
``settings(phases=[Phase.generate, Phase.shrink])`` will generate new examples
and shrink them, but will not run explicit examples or reuse previous failures,
while ``settings(phases=[Phase.explicit])`` will only run the explicit
examples.

.. _verbose-output:

~~~~~~~~~~~~~~~~~~~~~~~~~~
Seeing intermediate result
~~~~~~~~~~~~~~~~~~~~~~~~~~

To see what's going on while Hypothesis runs your tests, you can turn
up the verbosity setting. This works with both :func:`~hypothesis.core.find`
and :func:`@given <hypothesis.given>`.

.. doctest::

    >>> from hypothesis import find, settings, Verbosity
    >>> from hypothesis.strategies import lists, booleans
    >>> find(lists(integers()), any, settings=settings(verbosity=Verbosity.verbose))
    Tried non-satisfying example []
    Found satisfying example [-1198601713, -67, 116, -29578]
    Shrunk example to [-67, 116, -29578]
    Shrunk example to [116, -29578]
    Shrunk example to [-29578]
    Shrunk example to [-115]
    Shrunk example to [115]
    Shrunk example to [-57]
    Shrunk example to [29]
    Shrunk example to [-14]
    Shrunk example to [-7]
    Shrunk example to [4]
    Shrunk example to [2]
    Shrunk example to [1]
    [1]

The four levels are quiet, normal, verbose and debug. normal is the default,
while in quiet mode Hypothesis will not print anything out, not even the final
falsifying example. debug is basically verbose but a bit more so. You probably
don't want it.

You can also override the default by setting the environment variable
:envvar:`HYPOTHESIS_VERBOSITY_LEVEL` to the name of the level you want. So e.g.
setting ``HYPOTHESIS_VERBOSITY_LEVEL=verbose`` will run all your tests printing
intermediate results and errors.

If you are using :pypi:`pytest`, you may also need to
:doc:`disable output capturing for passing tests <pytest:capture>`.

-------------------------
Building settings objects
-------------------------

Settings can be created by calling :class:`~hypothesis.settings` with any of the available settings
values. Any absent ones will be set to defaults:

.. doctest::

    >>> from hypothesis import settings
    >>> settings().max_examples
    100
    >>> settings(max_examples=10).max_examples
    10


You can also copy settings from other settings:

.. doctest::

    >>> s = settings(max_examples=10)
    >>> t = settings(s, max_iterations=20)
    >>> s.max_examples
    10
    >>> t.max_iterations
    20
    >>> s.max_iterations
    1000
    >>> s.max_shrinks
    500
    >>> t.max_shrinks
    500

----------------
Default settings
----------------

At any given point in your program there is a current default settings,
available as ``settings.default``. As well as being a settings object in its own
right, all newly created settings objects which are not explicitly based off
another settings are based off the default, so will inherit any values that are
not explicitly set from it.

You can change the defaults by using profiles (see next section), but you can
also override them locally by using a settings object as a :ref:`context manager <python:context-managers>`


.. doctest::

    >>> with settings(max_examples=150):
    ...     print(settings.default.max_examples)
    ...     print(settings().max_examples)
    150
    150
    >>> settings().max_examples
    100

Note that after the block exits the default is returned to normal.

You can use this by nesting test definitions inside the context:

.. code:: python

    from hypothesis import given, settings

    with settings(max_examples=500):
        @given(integers())
        def test_this_thoroughly(x):
            pass

All settings objects created or tests defined inside the block will inherit their
defaults from the settings object used as the context. You can still override them
with custom defined settings of course.

Warning: If you use define test functions which don't use :func:`@given <hypothesis.given>`
inside a context block, these will not use the enclosing settings. This is because the context
manager only affects the definition, not the execution of the function.

.. _settings_profiles:

~~~~~~~~~~~~~~~~~
settings Profiles
~~~~~~~~~~~~~~~~~

Depending on your environment you may want different default settings.
For example: during development you may want to lower the number of examples
to speed up the tests. However, in a CI environment you may want more examples
so you are more likely to find bugs.

Hypothesis allows you to define different settings profiles. These profiles
can be loaded at any time.

Loading a profile changes the default settings but will not change the behavior
of tests that explicitly change the settings.

.. doctest::

    >>> from hypothesis import settings
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings().max_examples
    100
    >>> settings.load_profile("ci")
    >>> settings().max_examples
    1000

Instead of loading the profile and overriding the defaults you can retrieve profiles for
specific tests.

.. doctest::

    >>> with settings.get_profile("ci"):
    ...     print(settings().max_examples)
    ...
    1000

Optionally, you may define the environment variable to load a profile for you.
This is the suggested pattern for running your tests on CI.
The code below should run in a `conftest.py` or any setup/initialization section of your test suite.
If this variable is not defined the Hypothesis defined defaults will be loaded.

.. doctest::

    >>> import os
    >>> from hypothesis import settings, Verbosity
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings.register_profile("dev", max_examples=10)
    >>> settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
    >>> settings.load_profile(os.getenv(u'HYPOTHESIS_PROFILE', 'default'))

If you are using the hypothesis pytest plugin and your profiles are registered
by your conftest you can load one with the command line option ``--hypothesis-profile``.

.. code:: bash

    $ py.test tests --hypothesis-profile <profile-name>


~~~~~~~~
Timeouts
~~~~~~~~

The timeout functionality of Hypothesis is being deprecated, and will
eventually be removed. For the moment, the timeout setting can still be set
and the old default timeout of one minute remains.

If you want to future proof your code you can get
the future behaviour by setting it to the value ``hypothesis.unlimited``.

.. code:: python

    from hypothesis import given, settings, unlimited
    from hypothesis import strategies as st

    @settings(timeout=unlimited)
    @given(st.integers())
    def test_something_slow(i):
        ...

This will cause your code to run until it hits the normal Hypothesis example
limits, regardless of how long it takes. ``timeout=unlimited`` will remain a
valid setting after the timeout functionality has been deprecated (but will
then have its own deprecation cycle).

There is however now a timing related health check which is designed to catch
tests that run for ages by accident. If you really want your test to run
forever, the following code will enable that:

.. code:: python

    from hypothesis import given, settings, unlimited, HealthCheck
    from hypothesis import strategies as st

    @settings(timeout=unlimited, suppress_health_check=[
        HealthCheck.hung_test
    ])
    @given(st.integers())
    def test_something_slow(i):
        ...
