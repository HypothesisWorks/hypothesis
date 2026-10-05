RELEASE_TYPE: patch

This patch fixes the type annotation of
:func:`~hypothesis.extra.django.from_field`, which claimed to return a
strategy for instances of the field type rather than for values of the field.
