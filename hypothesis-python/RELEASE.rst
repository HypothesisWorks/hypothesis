RELEASE_TYPE: patch

This patch fixes :issue:`961`, where calling ``given()`` inline on a
bound method would fail to handle the ``self`` argument correctly.
