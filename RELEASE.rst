RELEASE_TYPE: patch

This changes how we compute the default ``average_size`` for all collection
strategies. Previously setting a ``max_size`` without setting an
``average_size`` would have the seemingly paradoxical effect of making data
generation *slower*, because it would raise the average size from its default.
Now setting ``max_size`` will either leave the default unchanged or lower it
from its default.

If you are currently experiencing this problem, this may make your tests
substantially faster. If you are not, this will likely have no effect on you.
