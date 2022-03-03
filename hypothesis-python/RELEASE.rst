RELEASE_TYPE: patch

This patch fixes a regression where the bound inner function
(``your_test.hypothesis.inner_test``) would be invoked with positional
arguments rather than passing them by name, which broke
:pypi:`pytest-asyncio` (:issue:`3245`).
