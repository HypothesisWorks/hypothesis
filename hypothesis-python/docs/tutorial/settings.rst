Configuring test settings
=========================

This page discusses how to configure the behavior of a single Hypothesis test, or of an entire test suite.

Configuring a single test
-------------------------

Hypothesis lets you configure the default behavior of a test using the |@settings| decorator. You can use settings to configure how many examples Hypothesis generates, how Hypothesis replays failing examples, and the verbosity level of the test, among others.

Using |@settings| on a single test looks like this:

.. code-block:: python

    from hypothesis import given, settings, strategies as st

    @given(st.integers())
    @settings(max_examples=200)
    def runs_200_times_instead_of_100(n):
        pass

You can put |@settings| either before or after |@given|. Both are equivalent.

Changing the number of examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have a test which is very expensive or very cheap to run, you can change the number of examples (inputs) Hypothesis generates with the |max_examples| setting:

.. code-block:: python

    from hypothesis import given, settings, strategies as st

    @given(st.integers())
    @settings(max_examples=5)
    def test(n):
        print("prints five times")

The default is 100 examples.

.. note::

    See :doc:`../explanation/example-count` for details on how |max_examples| interacts with other parts of Hypothesis.


Other settings options
~~~~~~~~~~~~~~~~~~~~~~

Here are a few of the more commonly used setting values:

* |settings.phases| controls which phases of Hypothesis run, like replaying from the database or generating new inputs.
* |settings.database| controls how and if Hypothesis replays failing examples.
* |settings.verbosity| can print debug information.
* |settings.derandomize| makes Hypothesis deterministic. (`Two kinds of testing <https://blog.nelhage.com/post/two-kinds-of-testing/>`__ discusses when and why you might want that).

.. note::

    See the |settings| reference for a full list of possible settings.


Changing settings across your test suite
----------------------------------------

In addition to configuring individual test functions with |@settings|, you can configure test behavior across your test suite using a settings profile. This might be useful for creating a development settings profile which runs fewer examples, or a settings profile in CI which connects to a separate database.

To create a settings profile, use |settings.register_profile|:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("fast", max_examples=10)

You can place this code in any file which gets loaded before your tests get run. This includes an ``__init__.py`` file in the test directory or any of the test files themselves. If using pytest, the standard location to place this code is in a ``confest.py`` file (though an ``__init__.py`` or test file will also work).

Note that registering a new profile will not affect tests until it is loaded with |settings.load_profile|:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("fast", max_examples=10)

    # any tests executed before loading this profile will still use the
    # default active profile of 100 examples.

    settings.load_profile("fast")

    # any tests executed after this point will use the active fast
    # profile of 10 examples.

There is no limit to the number of settings profiles you can create. Hypothesis creates a profile called ``"default"``, which is active by default. You can also explicitly make it active at any time using ``settings.load_profile("default")``, if for instance you wanted to revert a custom profile you had previously loaded.

Loading profiles from environment variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using an environment variable to load a settings profile is a useful trick for choosing a settings profile depending on the environment:

.. code-block:: pycon

    >>> import os
    >>> from hypothesis import settings, Verbosity
    >>> settings.register_profile("long", max_examples=1000)
    >>> settings.register_profile("fast", max_examples=10)
    >>> settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
    >>> settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

If using pytest, you can also easily select the active profile with ``--hypothesis-profile``:

.. code:: bash

    $ pytest --hypothesis-profile fast

See the :ref:`Hypothesis pytest plugin <pytest-plugin>`.

Using a configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~

For projects that prefer configuration files, Hypothesis can load settings from a ``hypothesis.ini`` file located at the project root. This file uses standard INI format and allows you to define settings profiles without writing Python code.

Hypothesis searches for ``hypothesis.ini`` in your project root (the directory containing ``.git/``, ``setup.py``, ``pyproject.toml``, or similar project markers).

Basic example
^^^^^^^^^^^^^

Create a ``hypothesis.ini`` file in your project root:

.. code-block:: ini

    [hypothesis]
    max_examples = 200
    deadline = 500

    [hypothesis:ci]
    max_examples = 1000
    deadline = None
    derandomize = true

    [hypothesis:fast]
    max_examples = 10

The ``[hypothesis]`` section configures the default profile, while ``[hypothesis:profile_name]`` sections define named profiles.

Supported settings
^^^^^^^^^^^^^^^^^^

You can configure any setting that can be passed to |settings|:

* **Boolean values**: ``true``/``false``, ``yes``/``no``, ``on``/``off``, ``1``/``0`` (case-insensitive)
* **Integer values**: ``max_examples = 100``
* **None values**: ``deadline = None`` or ``database = null``
* **Duration values**: ``deadline = 200`` (milliseconds) or ``deadline = 2s`` (seconds)
* **List values**: ``phases = explicit, generate, shrink`` (comma-separated)
* **String values**: ``verbosity = verbose``, ``backend = hypothesis``

Auto-loading a profile
^^^^^^^^^^^^^^^^^^^^^^

You can specify which profile to load by default using the ``load_profile`` key:

.. code-block:: ini

    [hypothesis]
    load_profile = development
    max_examples = 50

    [hypothesis:development]
    max_examples = 200

    [hypothesis:production]
    max_examples = 10000

When Hypothesis initializes, it will automatically load the ``development`` profile instead of the default profile.

Settings priority
^^^^^^^^^^^^^^^^^

Settings are applied in the following order (later items override earlier ones):

1. Built-in defaults (``default`` and ``ci`` profiles)
2. Settings from ``hypothesis.ini`` (if the file exists)
3. Programmatic |settings.register_profile| calls in your code
4. |@settings| decorators on individual tests

This means that ``hypothesis.ini`` provides a good baseline for your project, but individual tests can still override these settings as needed.

Complete example
^^^^^^^^^^^^^^^^

Here's a realistic ``hypothesis.ini`` for a typical project:

.. code-block:: ini

    [hypothesis]
    max_examples = 100
    deadline = 200
    verbosity = normal
    
    [hypothesis:ci]
    max_examples = 1000
    deadline = None
    derandomize = true
    print_blob = true
    suppress_health_check = too_slow
    
    [hypothesis:fast]
    max_examples = 10
    deadline = 50
    
    [hypothesis:debug]
    max_examples = 10
    verbosity = verbose
    print_blob = true
