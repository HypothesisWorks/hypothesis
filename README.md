<div align="center">
  <img src="https://raw.githubusercontent.com/HypothesisWorks/hypothesis/master/brand/dragonfly-rainbow.svg" width="300">
</div>

# Hypothesis

* [Website](https://hypothesis.works/)
* [Documentation](https://hypothesis.readthedocs.io/en/latest/)
* [Source code](https://github.com/hypothesisWorks/hypothesis/)
* [Contributing](https://github.com/HypothesisWorks/hypothesis/blob/master/CONTRIBUTING.rst)
* [Community](https://hypothesis.readthedocs.io/en/latest/community.html)

Hypothesis is the property-based testing library for Python. With Hypothesis, you write tests which should pass for all inputs in whatever range you describe, and let Hypothesis randomly choose which of those inputs to check - including edge cases you might not have thought about. For example:

```python
from hypothesis import given, strategies as st


@given(st.lists(st.integers()))
def test_matches_builtin(ls):
    assert sorted(ls) == my_sort(ls)
```

This randomized testing can catch bugs and edge cases that you didn't think of and wouldn't have found. In addition, when Hypothesis does find a bug, it doesn't just report any failing example — it reports the simplest possible one. This makes property-based tests a powerful tool for debugging, as well as testing.

For instance,

```python
def my_sort(ls):
    return sorted(set(ls))
```

fails with the simplest possible failing example:

```
Falsifying example: test_matches_builtin(ls=[0, 0])
```

### Installation

To install Hypothesis:

```
pip install hypothesis
```

There are also [optional extras available](https://hypothesis.readthedocs.io/en/latest/extras.html).
