RELEASE_TYPE: minor

Adds support for skipping shrinking. While shrinking is extremely helpful and important in general, it has the potential to be quite time consuming. It can be useful to observe a raw failure before choosing to allow the engine to try to shrink. [hypothesis-python](https://hypothesis.readthedocs.io/en/latest/settings.html#phases) already provides the ability to skip shrinking, so there is precedent for this being useful. While `hypothesis-ruby` does not have the concept of other "Phases" yet, we can still start off the API by using this concept.

Usage:

```
hypothesis(skip_phases: [:shrink]) do
  # Failures here will be displayed directly and shrinking will be avoided
end
```