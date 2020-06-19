RELEASE_TYPE: patch

This patch fixes an internal error when warning about the use of function-scoped fixtures
for parametrised tests where the parametrised value contained a ``%`` character.
Thanks to Bryant for reporting and fixing this bug!
