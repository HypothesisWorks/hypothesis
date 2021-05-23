RELEASE_TYPE: patch

This patch adds a `.hypothesis` property to invalid test functions, bringing
them inline with valid tests and fixing a bug where `pytest-asyncio` would
swallow the real error message and mistakenly raise a version incompatibility
error.