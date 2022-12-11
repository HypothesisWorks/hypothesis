RELEASE_TYPE: minor

This release improves our treatment of database keys, which based on (among other things)
the source code of your test function.  We now post-process this source to ignore
decorators, comments, trailing whitespace, and blank lines - so that you can add
:obj:`@example() <hypothesis.example>`\ s or make some small no-op edits to your code
without preventing replay of any known failing or covering examples.
