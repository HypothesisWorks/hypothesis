RELEASE_TYPE: patch

This patch fixes an error when importing our |django| extra if ``django.contrib.auth`` was not in `INSTALLED_APPS` (:issue:`3716`).

Thanks to Chris Wesseling for this fix!
