RELEASE_TYPE: minor

Hypothesis now reports some failing inputs by showing the call which constructed
an object, rather than the repr of the object.  This can be helpful when the default
repr does not include all relevant details, and will unlock further improvements
in a future version.

For now, we capture calls made via :func:`~hypothesis.strategies.builds`, and via
:ref:`SearchStrategy.map() <mapping>`.
