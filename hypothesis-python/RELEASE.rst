RELEASE_TYPE: minor

This release teaches Hypothesis to distinguish between errors based on the
`__cause__ or __context__ of otherwise identical exceptions
<https://docs.python.org/3/library/exceptions.html>`__, which is particularly
useful when internal errors can be wrapped by a library-specific or semantically
appropriate exception such as:

.. code-block:: python

    try:
        do_the_thing(foo, timeout=10)
    except Exception as err:
        raise FooError("Failed to do the thing") from err

Earlier versions of Hypothesis only see the ``FooError``, while we can now
distinguish a ``FooError`` raised because of e.g. an internal assertion from
one raised because of a ``TimeoutExceeded`` exception.
