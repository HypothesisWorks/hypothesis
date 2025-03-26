Settings
========

Hypothesis has default behavior for each property-based test. Sometimes, you need to adjust this behavior. The |@settings| decorator lets you adjust the behavior of a single test. Alternatively, settings profiles let you adjust test behavior across your test suite.

Among others, settings can control how many examples Hypothesis generates, how Hypothesis replays failing examples from the local database, and the verbosity level of the test.

Changing the settings of a test
-------------------------------

Using the |@settings| decorator on a single test looks like this:

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

.. TODO_DOCS
.. .. note::

..     See :doc:`../explanation/example-count` for details on how |max_examples| interacts with other parts of Hypothesis.


Other settings options
~~~~~~~~~~~~~~~~~~~~~~

Here are a few of the more commonly-used setting values:

* |settings.derandomize|, to make Hypothesis deterministic
* |settings.database|, to control how and if Hypothesis replays failing examples
* |settings.verbosity|, to print debug information
* |settings.phases|, to control which phases of Hypothesis run (database replay, generation, shrinking, etc)

.. note::

    See the |@settings| reference for a full list of possible settings.


Changing settings across your test suite
----------------------------------------

If you want to change the value of a setting for all tests, you can use a settings profile.

To create a settings profile, use |settings.register_profile|:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("my_profile_name", max_examples=200)

You can place this code in any file which gets loaded before your tests get run. This includes an ``__init__.py`` file in the test directory or any of the test files themselves. If using pytest, the standard location to place this code is in a ``confest.py`` file (though an ``__init__.py`` or test file will also work).

Note that a profile does not take effect until loaded with |settings.load_profile|:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("my_profile_name", max_examples=200)

    # any tests executed before loading this profile will still use the
    # default of 100 examples.

    settings.load_profile("myprofile")

    # any tests executed after this point will use your profile of
    # 200 examples.

You can register as many profiles as you want. The default profile created by Hypothesis is called ``"default"``, and is loaded by default. You can load it at any time using ``settings.load_profile("default")``, if for instance you want to revert a custom profile you had previously loaded.
