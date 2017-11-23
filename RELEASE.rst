RELEASE_TYPE: patch

This fixes the repr of strategies using lambda that are defined inside
decorators to include the lambda source.

This would mostly have been visible when using the
:ref:`statistics <statistics>` functionality - lambdas used for e.g. filtering
would have shown up with a ``<unknown>`` as their body. This can still happen,
but it should happen less often now.
