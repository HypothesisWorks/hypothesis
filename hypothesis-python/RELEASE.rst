RELEASE_TYPE: minor

This release makes us compatible with :pypi:`Django` 4.0, in particular by adding
support for use of :mod:`zoneinfo` timezones (though we respect the new
``USE_DEPRECATED_PYTZ`` setting if you need it).
