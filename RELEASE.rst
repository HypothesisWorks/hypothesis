RELEASE_TYPE: patch

This patch fixes :issue:`1017`, where instances of a list or tuple subtype
used as an argument to a strategy would be coerced to tuple.
