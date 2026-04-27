RELEASE_TYPE: patch

This release improves shrinking for a very specific category of generator:
If you have a primitive strategy such as :func:`~hypothesis.strategies.text()`
and write ``my_primitive_strategy | some_more_complicated_strategy``, values
produced by the second strategy can now be shrunk as if they had come
from the first strategy.
