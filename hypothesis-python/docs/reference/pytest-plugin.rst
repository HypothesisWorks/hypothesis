.. _pytest-plugin:

The Hypothesis pytest plugin
============================

Hypothesis includes a tiny plugin to improve integration with :pypi:`pytest`, which is activated by default (but does not affect other test runners). It aims to improve the integration between Hypothesis and Pytest by providing extra information and convenient access to config options.

- ``pytest --hypothesis-show-statistics`` can be used to :ref:`display test and data generation statistics <statistics>`.
- ``pytest --hypothesis-profile=<profile name>`` can be used to :ref:`load a settings profile <settings_profiles>`.
- ``pytest --hypothesis-verbosity=<level name>`` can be used to :ref:`override the current verbosity level <verbose-output>`.
- ``pytest --hypothesis-seed=<an int>`` can be used to :ref:`reproduce a failure with a particular seed <reproducing-with-seed>`.
- ``pytest --hypothesis-explain`` can be used to :ref:`temporarily enable the explain phase <phases>`.

Finally, all tests that are defined with Hypothesis automatically have ``@pytest.mark.hypothesis`` applied to them.  See :ref:`here for information on working with markers <pytest:mark examples>`.

.. note::
    Pytest will load the plugin automatically if Hypothesis is installed. You don't need to do anything at all to use it.

    If this causes problems, you can avoid loading the plugin with the ``-p no:hypothesispytest`` option.

.. _statistics:

Test statistics
---------------

You can see a number of statistics about executed tests by passing the command line argument ``--hypothesis-show-statistics``. This will include some general statistics about the test:

For example if you ran the following with ``--hypothesis-show-statistics``:

.. code-block:: python

  from hypothesis import given, strategies as st


  @given(st.integers())
  def test_integers(i):
      pass


You would see:

.. code-block:: none

    - during generate phase (0.06 seconds):
        - Typical runtimes: < 1ms, ~ 47% in data generation
        - 100 passing examples, 0 failing examples, 0 invalid examples
    - Stopped because settings.max_examples=100

The final "Stopped because" line tells you why Hypothesis stopped generating new examples. This is typically because we hit |max_examples|, but occasionally because we exhausted the search space or because shrinking was taking a very long time. This can be useful for understanding the behaviour of your tests.

In some cases (such as filtered and recursive strategies) you will see events mentioned which describe some aspect of the data generation:

.. code-block:: python

  from hypothesis import given, strategies as st


  @given(st.integers().filter(lambda x: x % 2 == 0))
  def test_even_integers(i):
      pass

You would see something like:

.. code-block:: none

  test_even_integers:

    - during generate phase (0.08 seconds):
        - Typical runtimes: < 1ms, ~ 57% in data generation
        - 100 passing examples, 0 failing examples, 12 invalid examples
        - Events:
          * 51.79%, Retried draw from integers().filter(lambda x: x % 2 == 0) to satisfy filter
          * 10.71%, Aborted test because unable to satisfy integers().filter(lambda x: x % 2 == 0)
    - Stopped because settings.max_examples=100
