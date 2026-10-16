RELEASE_TYPE: patch

If your test raised an exception while the underlying ``ConjectureData`` was
frozen but no ``StopTest`` was being suppressed - for example by freezing the
data explicitly, or in some async teardowns - the exception was replaced by a
``StopTest`` and the test silently passed. Such exceptions now propagate as
normal test failures (:issue:`4132`).
