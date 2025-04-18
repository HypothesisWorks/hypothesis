RELEASE_TYPE: patch

Prevent an unlikely but possible ``RuntimeError`` that can occur if
:func:`~hypothesis.internal.constants_ast.local_modules` is called while
:py:data:`sys.modules` is simultaneously modified, e.g. as a side effect
of imports executed from another thread.

