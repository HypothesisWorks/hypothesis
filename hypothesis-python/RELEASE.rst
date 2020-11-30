RELEASE_TYPE: patch

This patch teaches :func:`hypothesis.extra.django.from_field` to infer
more efficient strategies by inspecting (not just filtering by) field
validators for numeric and string fields (:issue:`1116`).
