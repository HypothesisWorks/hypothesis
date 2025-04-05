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

Hypothesis is the property-based testing library for Python. With Hypothesis, you write tests which should pass for all inputs in whatever range you describe, and let Hypothesis randomly choose which of those inputs to check - including edge cases you might not have thought about. For example:

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

New developers should start here, or with the more condensed :doc:`quickstart <quickstart>`.

.. rst-class:: column column2 top-right

:doc:`How-to guides <how-to/index>`
-----------------------------------

Practical guides for experienced developers.

.. rst-class:: column column2 bottom-left

:doc:`Explanations <explanation/index>`
---------------------------------------

Commentary oriented towards deepening your understanding of Hypothesis.

.. rst-class:: column column2 bottom-right

:doc:`API Reference <reference/index>`
--------------------------------------

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
    Extras <extras>
    Type hints <typing>
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
