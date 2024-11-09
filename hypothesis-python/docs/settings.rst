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
    :exclude-members: register_profile, get_profile, load_profile

.. _phases:

~~~~~~~~~~~~~~~~~~~~~
Controlling what runs
~~~~~~~~~~~~~~~~~~~~~

Hypothesis divides tests into logically distinct phases:

1. Running explicit examples :ref:`provided with the @example decorator <providing-explicit-examples>`.
2. Rerunning a selection of previously failing examples to reproduce a previously seen error.
3. Generating new examples.
4. Mutating examples for :ref:`targeted property-based testing <targeted-search>` (requires generate phase).
5. Attempting to shrink an example found in previous phases (other than phase 1 - explicit examples cannot be shrunk).
   This turns potentially large and complicated examples which may be hard to read into smaller and simpler ones.
6. Attempting to explain why your test failed (requires shrink phase).

.. note::

   The explain phase has two parts, each of which is best-effort - if Hypothesis can't
   find a useful explanation, we'll just print the minimal failing example.

   Following the first failure, Hypothesis will (:ref:`usually <phases>`) track which
   lines of code are always run on failing but never on passing inputs.
   This relies on :func:`python:sys.settrace`, and is therefore automatically disabled on
   PyPy or if you are using :pypi:`coverage` or a debugger.  If there are no clearly
   suspicious lines of code, :pep:`we refuse the temptation to guess <20>`.

   After shrinking to a minimal failing example, Hypothesis will try to find parts of
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


The phases setting provides you with fine grained control over which of these run,
with each phase corresponding to a value on the :class:`~hypothesis.Phase` enum:

.. autoclass:: hypothesis.Phase
   :members:

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
    >>> @given(lists(integers()))
    ... @settings(verbosity=Verbosity.verbose)
    ... def f(x):
    ...     assert not any(x)
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
:doc:`disable output capturing for passing tests <pytest:how-to/capture-stdout-stderr>`.

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
Settings profiles
~~~~~~~~~~~~~~~~~

Depending on your environment you may want different default settings.
For example: during development you may want to lower the number of examples
to speed up the tests. However, in a CI environment you may want more examples
so you are more likely to find bugs.

Hypothesis allows you to define different settings profiles. These profiles
can be loaded at any time.

.. automethod:: hypothesis.settings.register_profile
.. automethod:: hypothesis.settings.get_profile
.. automethod:: hypothesis.settings.load_profile

Loading a profile changes the default settings but will not change the behaviour
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
The code below should run in a ``conftest.py`` or any setup/initialization section of your test suite.
If this variable is not defined the Hypothesis defined defaults will be loaded.

.. code-block:: pycon

    >>> import os
    >>> from hypothesis import settings, Verbosity
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings.register_profile("dev", max_examples=10)
    >>> settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
    >>> settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

If you are using the hypothesis pytest plugin and your profiles are registered
by your conftest you can load one with the command line option ``--hypothesis-profile``.

.. code:: bash

    $ pytest tests --hypothesis-profile <profile-name>


Hypothesis comes with two built-in profiles, ``ci`` and ``default``.
``ci`` is set up to have good defaults for running in a CI environment, so emphasizes determinism, while the
``default`` settings are picked to be more likely to find bugs and to have a good workflow when used for local development.

Hypothesis will automatically detect certain common CI environments and use the ci profile automatically
when running in them.
In particular, if you wish to use the ``ci`` profile, setting the ``CI`` environment variable will do this.

This will still be the case if you register your own ci profile. For example, if you wanted to run more examples in CI, you might configure it as follows:

.. code-block:: python

    settings.register_profile(
        "ci",
        settings(
            settings.get_profile("ci"),
            max_examples=1000,
        ),
    )

This will configure your CI to run 1000 examples per test rather than the default of 100, and this change will automatically be picked up when running on a CI server.

.. _healthchecks:

-------------
Health checks
-------------

Hypothesis' health checks are designed to detect and warn you about performance
problems where your tests are slow, inefficient, or generating very large examples.

If this is expected, e.g. when generating large arrays or dataframes, you can selectively
disable them with the :obj:`~hypothesis.settings.suppress_health_check` setting.
The argument for this parameter is a list with elements drawn from any of
the class-level attributes of the HealthCheck class.
Using a value of ``list(HealthCheck)`` will disable all health checks.

.. autoclass:: hypothesis.HealthCheck
   :undoc-members:
   :inherited-members:
   :exclude-members: all
