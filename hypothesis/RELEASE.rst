RELEASE_TYPE: patch

:func:`~hypothesis.strategies.dates` now raises ``InvalidArgument`` if a
:class:`~python:datetime.datetime` is passed as ``min_value`` or ``max_value``.
Because ``datetime`` is a subclass of :class:`~python:datetime.date`, such
bounds were previously accepted and then failed with a confusing ``TypeError``
while generating examples.
