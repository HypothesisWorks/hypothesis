<div align="center">
  <img src="./brand/dragonfly-rainbow.svg" width="300">
</div>

# Hypothesis

* [Website](https://hypothesis.works/)
* [Documentation](https://hypothesis.readthedocs.io/en/latest/)
* [Source code](https://github.com/hypothesisWorks/hypothesis/)
* [Contributing](https://github.com/HypothesisWorks/hypothesis/blob/master/CONTRIBUTING.rst)
* [Community](https://hypothesis.readthedocs.io/en/latest/community.html)

Hypothesis is the property-based testing library for Python. A property-based test asserts something for *all* inputs, and lets Hypothesis generate them — including inputs you may not have thought of.

```python
from hypothesis import given, strategies as st


@given(st.lists(st.integers() | st.floats()))
def test_matches_builtin(ls):
    assert sorted(ls) == my_sort(ls)
```

Additionally, when a property fails, Hypothesis doesn't just report any failing example — it reports the simplest possible one. This makes property-based tests a powerful tool for debugging, as well as testing.

For instance,

```python
def my_sort(ls):
    return list(reversed(sorted(ls, reverse=True)))
```

fails with:

```
Falsifying example: test_matches_builtin(ls=[0, math.nan])
```

### Installation

To install Hypothesis:

```
pip install hypothesis
```

There are also [optional extras available](https://hypothesis.readthedocs.io/en/latest/extras.html).
