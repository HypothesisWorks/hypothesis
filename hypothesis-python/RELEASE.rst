RELEASE_TYPE: patch

This patch changes the resolution order used by `to_jsonable()` to allow custom
classes to control their json representation by providing a `to_json()` even
when a more general resolution strategy might apply.
