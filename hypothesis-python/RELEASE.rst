RELEASE_TYPE: minor

This release makes setting attributes of the :class:`hypothesis.settings`
class an explicit error.  This has never had any effect, but could mislead
users who confused it with the current settings *instance*
``hypothesis.settings.default`` (which is also immutable).  You can change
the global settings with :ref:` settings profiles<settings_profiles>`.
