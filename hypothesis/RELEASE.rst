RELEASE_TYPE: patch

This patch uses `dateutil.tz.available_iana_timezones` when available
on :pypi:python-dateutil >= 3.0 to avoid a :class:DeprecationWarning when
importing `dateutil.zoneinfo` (:issue:4934).

Thanks to Lucas Meyer for this contribution!
