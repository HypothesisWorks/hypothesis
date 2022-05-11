RELEASE_TYPE: patch

This patch by Cheuk Ting Ho makes it an explicit error to call :func:`~hypothesis.strategies.from_type`
or :func:`~hypothesis.strategies.register_type_strategy` with types that have no runtime instances (:issue:`3280`).
