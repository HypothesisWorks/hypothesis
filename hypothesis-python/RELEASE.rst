RELEASE_TYPE: patch

Building on recent releases, :func:`~hypothesis.strategies.characters`
now accepts _any_ ``codec=``, not just ``"utf-8"`` and ``"ascii"``.

This includes standard codecs from the :mod:`codecs` module and their
aliases, platform specific and user-registered codecs if they are
available, and `python-specific text encodings
<https://docs.python.org/3/library/codecs.html#python-specific-encodings>`__
(but not text transforms or binary transforms).
