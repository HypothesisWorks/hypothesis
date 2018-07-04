RELEASE_TYPE: patch

This release fixes a mostly theoretical bug where certain usage of the internal
API could trigger an assertion error inside Hypothesis. It is unlikely that
this problem is even possible to trigger through the public API.
