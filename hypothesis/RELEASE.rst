RELEASE_TYPE: patch

This patch fixes a bug for users of our |PrimitiveProvider| interface, where ``draw_integer`` could incorrectly reuse weights from an earlier draw (:issue:`4908`).
