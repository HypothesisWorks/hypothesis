RELEASE_TYPE: patch

This release enables direct use of keyword arguments in
:func:`~hypothesis.settings.settings.register_profile`.

- :func:`~hypothesis.settings.settings.register_profile` no longer
  requires a :class:`~hypothesis.settings.settings` instance to be
  passed in: the keyword arguments used to construct the instance can
  be passed in directly.

  Alternatively, such an instance can be passed in, along with keyword
  arguments which override any settings present in the instance.

Thanks to Jacek Generowicz for this feature.
