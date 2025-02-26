<div align="center">
  <img src="./brand/dragonfly-rainbow.svg" width="300">
</div>

# Hypothesis

* [Website](https://hypothesis.works/)
* [Documentation](https://hypothesis.readthedocs.io/en/latest/)
* [Source code](https://github.com/hypothesisWorks/hypothesis/)
* [Contributing](https://github.com/HypothesisWorks/hypothesis/blob/master/CONTRIBUTING.rst)
* [Community](https://hypothesis.readthedocs.io/en/latest/community.html)

Hypothesis is the canonical property-based testing library for Python. A property-based test asserts something for *all* inputs, and lets Hypothesis generate them — including inputs you may not have thought of.

```python
from hypothesis import given, strategies as st


@given(st.lists(st.integers() | st.floats()))
def test_matches_builtin(lst):
    assert sorted(lst) == my_sort(lst)
```

Additionally, when a property fails, Hypothesis doesn't just report any failing example — it reports the simplest possible one. This makes property-based tests a powerful tool for debugging, as well as testing.

For instance,

```python
my_sort = lambda l: list(reversed(sorted(l, reverse=True)))
```

fails with:

```
Falsifying example: test_matches_builtin(lst=[0, math.nan])
```

### Installation

To install Hypothesis:

```
pip install hypothesis
```
