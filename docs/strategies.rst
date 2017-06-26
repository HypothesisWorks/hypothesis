=============================
Projects extending Hypothesis
=============================

The following is a non-exhaustive list of open source projects that make
Hypothesis strategies available. If you're aware of any others please add them
the list!  The only inclusion criterion right now is that if it's a Python
library then it should be available on pypi.

* `hs-dbus-signature <https://github.com/stratis-storage/hs-dbus-signature>`_ - strategy to generate arbitrary D-Bus signatures
* `hypothesis-regex <https://github.com/maximkulkin/hypothesis-regex>`_ - strategy
  to generate strings that match given regular expression (merged into Hypothesis as
  the :func:`~hypothesis.strategies.strings_matching_regex` strategy).
* `lollipop-hypothesis <https://github.com/maximkulkin/lollipop-hypothesis>`_ -
  strategy to generate data based on
  `Lollipop <https://github.com/maximkulkin/lollipop>`_ schema definitions.
* `hypothesis-fspaths <https://github.com/lazka/hypothesis-fspaths>`_ -
  strategy to generate filesystem paths.

If you're thinking about writing an extension, consider naming it
``hypothesis-{something}`` - a standard prefix makes the community more
visible and searching for extensions easier.
