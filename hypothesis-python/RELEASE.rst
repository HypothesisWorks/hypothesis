RELEASE_TYPE: patch

This patch fixes an error when importing :ref:`our django extra <hypothesis-django>` (via ``hypothesis.extra.django``) if ``django.contrib.auth`` was not in ``INSTALLED_APPS`` (:issue:`3716`).

Thanks to Chris Wesseling for this fix!
