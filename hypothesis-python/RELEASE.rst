RELEASE_TYPE: minor

This release supports passing a :class:`~python:datetime.timedelta` as the
:obj:`~hypothesis.settings.deadline` setting, so you no longer have to remember
that the number is in milliseconds (:issue:`1900`).

Thanks to Damon Francisco for this change!
