RELEASE_TYPE: minor

This release follows :pypi:`pytest` in considering :class:`SystemExit` and
:class:`GeneratorExit` exceptions to be test failures, meaning that we will
shink to minimal examples and check for flakiness even though they subclass
:class:`BaseException` directly (:issue:`2223`).

:class:`KeyboardInterrupt` continues to interrupt everything, and will be
re-raised immediately.
