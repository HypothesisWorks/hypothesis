RELEASE_TYPE: minor

Hypothesis now emits deprecation warnings if you are using the legacy
SQLite example database format, or the tool for merging them. These were
already documented as deprecated, so this doesn't change their deprecation
status, only that we warn about it.
