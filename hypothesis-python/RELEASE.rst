RELEASE_TYPE: major

Welcome to the next major version of Hypothesis!

There are no new features here, as we release those in minor versions.
Instead, 6.0 is a chance for us to remove deprecated features (many already
converted into no-ops), and turn a variety of warnings into errors.

If you were running on the last version of Hypothesis 5.x *without any
Hypothesis deprecation warnings*, this will be a very boring upgrade.
**In fact, nothing will change for you at all.**

Changes
~~~~~~~
- Many functions now use :pep:`3102` keyword-only arguments where passing positional
  arguments :ref:`was deprecated since 5.5 <v5.5.0>`.
- :func:`hypothesis.extra.django.from_model` no longer accepts ``model`` as a
  keyword argument, where it could conflict with fields named "model".
- :func:`~hypothesis.strategies.randoms` now defaults to ``use_true_random=False``.
- :func:`~hypothesis.strategies.complex_numbers` no longer accepts
  ``min_magnitude=None``; either use ``min_magnitude=0`` or just omit the argument.
- ``hypothesis.provisional.ip4_addr_strings`` and ``ip6_addr_strings`` are removed
  in favor of :func:`ip_addresses(v=...).map(str) <hypothesis.strategies.ip_addresses>`.
- :func:`~hypothesis.strategies.register_type_strategy` no longer accepts generic
  types with type arguments, which were always pretty badly broken.
- Using function-scoped pytest fixtures is now a health-check error, instead of a warning.

.. tip::
    The :command:`hypothesis codemod` command can automatically refactor your code,
    particularly to convert positional to keyword arguments where those are now
    required.
