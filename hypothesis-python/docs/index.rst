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

    @given(st.lists(st.integers() | st.floats(allow_nan=False)))
    def test_sort_correct(lst):
        # We can check my_sort against a trusted reference on many inputs:
        assert my_sort(lst) == sorted(lst)

        # We can also check if the result is correct, without our test knowing
        # how to find it.  e.g., sorting returns the same elements, in order:
        result = my_sort(lst)
        assert collections.Counter(lst) == collections.Counter(result)
        assert all(a <= b for a, b in zip(result, result[1:]))

        # Or we can just look for bugs using incomplete specifications, e.g.
        assert my_sort(lst) == my_sort(my_sort(lst))  # idempotence
        assert my_sort(lst) == my_sort(shuffled(lst))  # input order irrelevant

    @given(
        st.recursive(
            st.from_type(None | bool | int | float | str),
            lambda elem: st.lists(elem) | st.dictionaries(st.text(), elem),
        )
    )
    def test_json_roundtrip(value):
        assume(value == value)  # exclude e.g. NaN
        assert value == json.loads(json.dumps(value))

You should start with the :doc:`tutorial <tutorial/index>`, or alternatively the more condensed :doc:`quickstart <quickstart>`.

.. rst-class:: row

.. rst-class:: column column2 top-left

:doc:`Tutorial <tutorial/index>`
---------------------------------

An introduction to Hypothesis.

New users should start here, or with the more condensed :doc:`quickstart <quickstart>`.

.. rst-class:: column column2 top-right

:doc:`How-to guides <how-to/index>`
-----------------------------------

Practical guides for applying Hypothesis in specific scenarios.

.. rst-class:: column column2 bottom-left

:doc:`Explanations <explanation/index>`
---------------------------------------

Commentary oriented towards deepening your understanding of Hypothesis.

.. rst-class:: column column2 bottom-right

:doc:`API Reference <reference/index>`
--------------------------------------

Technical API reference.

.. rst-class:: row

.. toctree::
  :maxdepth: 1
  :hidden:

  quickstart
  tutorial/index
  how-to/index
  explanation/index
  reference/index
  stateful
  Extras <extras>
  changelog

.. toctree::
  :maxdepth: 1
  :hidden:
  :caption: About Hypothesis

  development
  compatibility
  usage
  extensions
  packaging
  community
