RELEASE_TYPE: patch

This patch improves strategy inference in :mod:`hypothesis.extra.django`
to account for some validators in addition to field type - see
:issue:`1116` for ongoing work in this space.

Specifically, if a :class:`~django:django.db.models.fields.CharField` or
:class:`~django:django.db.models.fields.TextField` has an attached
:class:`~django:django.core.validators.RegexValidator`, we now use
:func:`~hypothesis.strategies.from_regex` instead of
:func:`~hypothesis.strategies.text` as the underlying strategy.
This allows us to generate examples of the default
:class:`~django:django.contrib.auth.models.User` model, closing :issue:`1112`.
