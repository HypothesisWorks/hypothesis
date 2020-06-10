RELEASE_TYPE: patch

If you pass a :class:`python:list` or :class:`python:tuple` where a
strategy was expected, the error message now mentions
:func:`~hypothesis.strategies.sampled_from` as an example strategy.

Thanks to the enthusiastic participants in the `PyCon Mentored Sprints
<https://us.pycon.org/2020/hatchery/mentoredsprints/>`__ who suggested
adding this hint.
