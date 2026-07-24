RELEASE_TYPE: minor

This release adds support for generating timezone-aware datetimes in
:ref:`hypothesis.extra.pandas <hypothesis-pandas>`.  You can now pass a
:class:`~pandas.DatetimeTZDtype` - such as ``"datetime64[ns, UTC]"`` - as the
``dtype`` of a :func:`~hypothesis.extra.pandas.series`,
:func:`~hypothesis.extra.pandas.indexes`, or
:func:`~hypothesis.extra.pandas.column`, and every value will share that single
timezone (the only arrangement pandas supports outside of the ``object``
dtype).  The datetime resolution is taken from the dtype, so you can also
generate e.g. ``"datetime64[us, UTC]"`` columns, and for UTC and other
fixed-offset timezones the generated values cover the full range representable
at that resolution - which for coarser units is far wider than the
``datetime64[ns]`` bounds of roughly 1677-2262 (:issue:`4020`).

Timezone-aware generation requires pandas >= 2.1: earlier versions silently
coerce other resolutions to nanoseconds, or crash when displaying values
outside the nanosecond-representable range.  Generated values include ``NaT``
unless you pass an elements strategy which excludes it.
