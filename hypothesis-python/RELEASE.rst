RELEASE_TYPE: patch

This release fixes the type hint on `register_type_strategy`. The second
argument to `register_type_strategy` must either be a `SearchStrategy`,
or a callable which takes a `type` and returns a `SearchStrategy`.