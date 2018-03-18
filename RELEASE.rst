RELEASE_TYPE: patch

This patch fixes an internal error introduced in 3.48.0, where a check
for the Django test runner would expose import-time errors in Django
configuration (:issue:`1167`).
