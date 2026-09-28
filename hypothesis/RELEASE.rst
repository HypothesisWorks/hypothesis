RELEASE_TYPE: patch

Tracebacks for failing tests no longer point at the wrong line (:issue:`4681`).
Hypothesis used to claim that its internal wrapper functions were defined where
your test is, which meant the quoted source line - and the carets under it -
could refer to somewhere else entirely.

Tracebacks are also tidier: we now strip our own frames from the middle as well
as the start, so that e.g. drawing from a strategy which raises no longer shows
the internals in between.
