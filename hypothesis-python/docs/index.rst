.. raw:: html

     <!-- adapted from https://docs.django-cms.org/en/release-4.1.x/, with thanks -->

    <style>
        .row {
           clear: both;
        }

        .column img {border: 1px solid gray;}

        @media only screen and (min-width: 1000px) {

            .column {
                padding-left: 5px;
                padding-right: 5px;
                float: left;
            }

            .column2  {
                width: calc(50% - 11px);
                position: relative;
            }
            .column2:before {
                padding-top: 61.8%;
                content: "";
                display: block;
                float: left;
            }
            .top-left {
                border-right: 1px solid var(--color-background-border);
                border-bottom: 1px solid var(--color-background-border);
            }
            .top-right {
                border-bottom: 1px solid var(--color-background-border);
            }
            .bottom-left {
                border-right: 1px solid var(--color-background-border);
            }
        }
    </style>

Welcome to Hypothesis!
======================

Hypothesis is the Python library for `property-based testing <https://en.wikipedia.org/wiki/Software_testing#Property_testing>`_, a powerful addition to unit testing.

In a normal unit test, you create test inputs manually. Hypothesis instead lets you write tests which should hold for *all* inputs, and then randomly generates those test inputs for you. This can end up testing behavior you wouldn't normally have thought of.

.. code-block:: python

    from hypothesis import given, strategies as st

    @given(st.lists(st.integers() | st.floats()))
    def test_sort_correct(lst):
        # lst is a random list of numbers
        assert my_sort(lst) == sorted(lst)

    test_sort_correct()

You should start with the :doc:`tutorials <tutorial/index>`, or the more condensed :doc:`quickstart <quickstart>`.

.. rst-class:: clearfix row

.. rst-class:: column column2 top-left

:doc:`Tutorials <tutorial/index>`
----------------------------------

New developers should **start here**, or with the more condensed :doc:`quickstart <quickstart>`.

.. rst-class:: column column2 top-right

:doc:`How-to guides <how-to/index>`
-----------------------------------

Practical guides for experienced developers.

.. rst-class:: column column2 bottom-left

:doc:`Explanations <explanation/index>`
---------------------------------------

Conceptual explanations of Hypothesis concepts.

.. rst-class:: column column2 bottom-right

:doc:`Reference <reference/index>`
----------------------------------

Technical API reference.

.. rst-class:: clearfix row

.. toctree::
    :maxdepth: 1
    :hidden:

    quickstart
    tutorial/index
    how-to/index
    explanation/index
    reference/index
    changelog

.. toctree::
    :maxdepth: 1
    :hidden:
    :caption: About Hypothesis

    compatibility
    development
    usage
    extensions
    packaging
    community
    endorsements
