RELEASE_TYPE: patch

This patch makes the stringification of lambdas, and as
a result certain automatic filter rewriting operations,
more robust. This fixes :issue:`4498`, where a lambda
was mistakenly identified as the identity operator due
to :func:`inspect.getsource` only returning the first
line of the lambda definition.

As a result, the ``repr`` of strategies filtered or
mapped by lambda functions may change slightly.
