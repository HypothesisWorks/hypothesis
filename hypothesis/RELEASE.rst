RELEASE_TYPE: patch

This patch fixes a bug where resolving recursive forward references in
|st.from_type| (such as ``A = list[Union["A", str]]``, added in :v:`6.152.11`)
could recurse until it hit the interpreter's recursion limit before falling
back to a deferred strategy.  Because this depended on the ambient stack depth,
it occasionally surfaced as a spurious ``RecursionError`` or other flaky
failure.  We now break the cycle eagerly by deferring, so resolution uses a
small and constant amount of stack regardless of how deeply nested the
reference is.
