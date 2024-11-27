RELEASE_TYPE: minor

This release adds :class:`~hypothesis.database.BackgroundWriteDatabase`, a new database backend that defers writes on the wrapped database to a background thread. This allows for low-overhead writes in performance-critical environments like fuzzing.
