RELEASE_TYPE: minor

This release contains a massive cleanup of the Hypothesis for Django extra:

- ``hypothesis.extra.django.models.models()`` is deprecated in favor of
  :func:`hypothesis.extra.django.from_model`.
- ``hypothesis.extra.django.models.add_default_field_mapping()`` is deprecated
  in favor of :func:`hypothesis.extra.django.register_field_strategy`.
- :func:`~hypothesis.extra.django.from_model` does not infer a strategy for
  nullable fields or fields with a default unless passed ``infer``, like
  :func:`~hypothesis.strategies.builds`.
  ``models.models()`` would usually but not always infer, and a special
  ``default_value`` marker object was required to disable inference.
