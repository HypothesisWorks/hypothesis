RELEASE_TYPE: minor

Hypothesis now raises an error if you passed a strategy as the ``alphabet=``
argument to :func:`~hypothesis.strategies.text`, and it generated something
which was not a length-one string.  This has never been supported, we're just
adding explicit validation to catch cases like `this StackOverflow question
<https://stackoverflow.com/a/74336909/9297601>`__.
