RELEASE_TYPE: minor

This release supports strategy inference for more field types in Django
:func:`~hypothesis.extra.django.models` - you can now omit an argument for
Date, Time, Duration, Slug, IP Address, and UUID fields.  (:issue:`642`)

Strategy generation for fields with grouped choices now selects choices from
each group, instead of selecting from the group names.
