========
Settings
========

Hypothesis tries to have good defaults for its behaviour, but sometimes that's
not enough and you need to tweak it.

The mechanism for doing this is the :class:`~hypothesis.settings` object.
You can set up a @given based test to use this using a settings decorator:

:func:`@given <hypothesis.core.given>` invocation as follows:

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
        database, perform_health_check, suppress_health_check, buffer_size

.. _verbose-output:

~~~~~~~~~~~~~~~~~~~~~~~~~~
Seeing intermediate result
~~~~~~~~~~~~~~~~~~~~~~~~~~

To see what's going on while Hypothesis runs your tests, you can turn
up the verbosity setting. This works with both :func:`~hypothesis.core.find`
and :func:`@given <hypothesis.core.given>`.

.. doctest::

    >>> from hypothesis import find, settings, Verbosity
    >>> from hypothesis.strategies import lists, booleans
    >>> find(lists(integers()), any, settings=settings(verbosity=Verbosity.verbose))
    Found satisfying example [-208]
    Shrunk example to [-208]
    Shrunk example to [208]
    Shrunk example to [104]
    Shrunk example to [52]
    Shrunk example to [26]
    Shrunk example to [13]
    Shrunk example to [6]
    Shrunk example to [3]
    Shrunk example to [1]
    [1]

The four levels are quiet, normal, verbose and debug. normal is the default,
while in quiet Hypothesis will not print anything out, even the final
falsifying example. debug is basically verbose but a bit more so. You probably
don't want it.

You can also override the default by setting the environment variable
:envvar:`HYPOTHESIS_VERBOSITY_LEVEL` to the name of the level you want. So e.g.
setting ``HYPOTHESIS_VERBOSITY_LEVEL=verbose`` will run all your tests printing
intermediate results and errors.

-------------------------
Building settings objects
-------------------------

settings can be created by calling settings with any of the available settings
values. Any absent ones will be set to defaults:

.. doctest::

    >>> from hypothesis import settings
    >>> settings()  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    settings(buffer_size=8192, database_file='...', derandomize=False,
             max_examples=200, max_iterations=1000, max_mutations=10,
             max_shrinks=500, min_satisfying_examples=5, perform_health_check=True,
             phases=..., report_statistics=..., stateful_step_count=50, strict=False,
             suppress_health_check=[], timeout=60, verbosity=Verbosity.normal)
    >>> settings().max_examples
    200
    >>> settings(max_examples=10).max_examples
    10


You can also copy settings off other settings:

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
available as settings.default. As well as being a settings object in its own
right, all newly created settings objects which are not explicitly based off
another settings are based off the default, so will inherit any values that are
not explicitly set from it.

You can change the defaults by using profiles (see next section), but you can
also override them locally by using a settings object as a :ref:`context manager <python:context-managers>`


.. doctest::

  >>> with settings(max_examples=150):
  ...     print(settings.default.max_examples)
  ...     print(settings().max_examples)
  ...
  150
  150
  >>> settings().max_examples
  200

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

Warning: If you use define test functions which don't use @given inside a context
block, these will not use the enclosing settings. This is because the context
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
    >>> settings.register_profile("ci", settings(max_examples=1000))
    >>> settings().max_examples
    200
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
    >>> from hypothesis import settings
    >>> settings.register_profile("ci", settings(max_examples=1000))
    >>> settings.register_profile("dev", settings(max_examples=10))
    >>> settings.register_profile("debug", settings(max_examples=10, verbosity=Verbosity.verbose))
    >>> settings.load_profile(os.getenv(u'HYPOTHESIS_PROFILE', 'default'))

If you are using the hypothesis pytest plugin and your profiles are registered
by your conftest you can load one with the command line option ``--hypothesis-profile``.

.. code:: bash

    $ py.test tests --hypothesis-profile <profile-name>
