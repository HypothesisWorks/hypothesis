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

* |settings.derandomize| makes Hypothesis deterministic. (`Two kinds of testing <https://blog.nelhage.com/post/two-kinds-of-testing/>`__ discusses when and why you might want that).
* |settings.database| controls how and if Hypothesis replays failing examples.
* |settings.verbosity| to print debug information.
* |settings.phases| controls which phases of Hypothesis run, like replaying from the database or generating new inputs.

.. note::

    See the |@settings| reference for a full list of possible settings.


Changing settings across your test suite
----------------------------------------

In addition to configuring individual test functions with |@settings|, you can configure test behavior across your test suite using a settings profile.

To create a settings profile, use |settings.register_profile|:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("my_profile_name", max_examples=200)

You can place this code in any file which gets loaded before your tests get run. This includes an ``__init__.py`` file in the test directory or any of the test files themselves. If using pytest, the standard location to place this code is in a ``confest.py`` file (though an ``__init__.py`` or test file will also work).

Note that registering a new profile will not affect tests until it is loaded with |settings.load_profile|:

.. code-block:: python

    from hypothesis import HealthCheck, settings

    settings.register_profile("my_profile_name", max_examples=200)

    # any tests executed before loading this profile will still use the
    # default of 100 examples.

    settings.load_profile("my_profile_name")

    # any tests executed after this point will use your profile of
    # 200 examples.

There is no limit to the number of settings profiles you can create. Hypothesis creates a profile called ``"default"``, which is loaded by default. You can also explicitly load it at any time using ``settings.load_profile("default")``, if for instance you want to revert a custom profile you had previously loaded.
