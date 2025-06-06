RELEASE_TYPE: patch

This patch adresses a `RuntimeError` upon import if certain `django.contrib`
packages are not in `INSTALLED_APPS`. (:issue:`3716`)

Thanks to Chris Wesseling for this fix!
