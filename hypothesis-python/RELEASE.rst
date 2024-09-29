RELEASE_TYPE: patch

This patch fixes an internal error when the ``__context__``
attribute of a raised exception leads to a cycle (:issue:`4115`).
