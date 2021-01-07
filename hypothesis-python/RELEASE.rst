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
- :func:`hypothesis.extra.django.from_model` no longer accepts ``model`` as a
  keyword argument, where it could conflict with fields named "model".
- :func:`~hypothesis.strategies.randoms` now defaults to ``use_true_random=False``.
- :func:`~hypothesis.strategies.complex_numbers` no longer accepts
  ``min_magnitude=None``; either use ``min_magnitude=0`` or just omit the argument.
- ``hypothesis.provisional.ip4_addr_strings`` and ``ip6_addr_strings`` are removed
  in favor of :func:`ip_addresses(v=...).map(str) <hypothesis.strategies.ip_addresses>`.
