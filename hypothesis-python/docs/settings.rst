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

.. autoclass:: hypothesis.settings
    :members:
    :exclude-members: register_profile, get_profile, load_profile, buffer_size

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
with each phase corresponding to a value on the :class:`~hypothesis.Phase` enum:

.. class:: hypothesis.Phase

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
up the verbosity setting.

.. code-block:: pycon

    >>> from hypothesis import find, settings, Verbosity
    >>> from hypothesis.strategies import lists, integers
    >>> @given(lists(integers())
    ... @settings(verbosity=Verbosity.verbose))
    ... def f(x): assert not any(x)
    ... f()
    Trying example: []
    Falsifying example: [-1198601713, -67, 116, -29578]
    Shrunk example to [-1198601713]
    Shrunk example to [-1198601600]
    Shrunk example to [-1191228800]
    Shrunk example to [-8421504]
    Shrunk example to [-32896]
    Shrunk example to [-128]
    Shrunk example to [64]
    Shrunk example to [32]
    Shrunk example to [16]
    Shrunk example to [8]
    Shrunk example to [4]
    Shrunk example to [3]
    Shrunk example to [2]
    Shrunk example to [1]
    [1]

The four levels are quiet, normal, verbose and debug. normal is the default,
while in quiet mode Hypothesis will not print anything out, not even the final
falsifying example. debug is basically verbose but a bit more so. You probably
don't want it.

If you are using :pypi:`pytest`, you may also need to
:doc:`disable output capturing for passing tests <pytest:capture>`.

-------------------------
Building settings objects
-------------------------

Settings can be created by calling :class:`~hypothesis.settings` with any of the available settings
values. Any absent ones will be set to defaults:

.. code-block:: pycon

    >>> from hypothesis import settings
    >>> settings().max_examples
    100
    >>> settings(max_examples=10).max_examples
    10

You can also pass a 'parent' settings object as the first argument,
and any settings you do not specify as keyword arguments will be
copied from the parent settings:

.. code-block:: pycon

    >>> parent = settings(max_examples=10)
    >>> child = settings(parent, deadline=None)
    >>> parent.max_examples == child.max_examples == 10
    True
    >>> parent.deadline
    200
    >>> child.deadline is None
    True

----------------
Default settings
----------------

At any given point in your program there is a current default settings,
available as ``settings.default``. As well as being a settings object in its own
right, all newly created settings objects which are not explicitly based off
another settings are based off the default, so will inherit any values that are
not explicitly set from it.

You can change the defaults by using profiles.

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

.. autoclass:: hypothesis.settings
    :members: register_profile, get_profile, load_profile

Loading a profile changes the default settings but will not change the behavior
of tests that explicitly change the settings.

.. code-block:: pycon

    >>> from hypothesis import settings
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings().max_examples
    100
    >>> settings.load_profile("ci")
    >>> settings().max_examples
    1000

Instead of loading the profile and overriding the defaults you can retrieve profiles for
specific tests.

.. code-block:: pycon

    >>> settings.get_profile("ci").max_examples
    1000

Optionally, you may define the environment variable to load a profile for you.
This is the suggested pattern for running your tests on CI.
The code below should run in a `conftest.py` or any setup/initialization section of your test suite.
If this variable is not defined the Hypothesis defined defaults will be loaded.

.. code-block:: pycon

    >>> import os
    >>> from hypothesis import settings, Verbosity
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings.register_profile("dev", max_examples=10)
    >>> settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
    >>> settings.load_profile(os.getenv(u'HYPOTHESIS_PROFILE', 'default'))

If you are using the hypothesis pytest plugin and your profiles are registered
by your conftest you can load one with the command line option ``--hypothesis-profile``.

.. code:: bash

    $ pytest tests --hypothesis-profile <profile-name>
