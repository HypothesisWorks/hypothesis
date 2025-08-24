TYPE: patch

This patch further improves stringification of lambdas, by
never returning a lambda source unless it is confirmed to
compile to the same code object. This stricter check makes
it possible to widen the search for a matching source block,
so that it can often be found even if the file has been
edited.
