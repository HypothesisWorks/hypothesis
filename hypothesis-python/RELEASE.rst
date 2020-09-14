RELEASE_TYPE: patch

This patch changes some internal :obj:`python:struct.Struct.format` strings
from ``bytes`` to ``str``, to avoid :class:`python:BytesWarning` when running
`python -bb <https://docs.python.org/3/using/cmdline.html#cmdoption-b>`__.

Thanks to everyone involved in `pytest-xdist issue 596
<https://github.com/pytest-dev/pytest-xdist/issues/596>`__,
:bpo:`16349`, :bpo:`21071`, and :bpo:`41777` for their work on this -
it was a remarkably subtle issue!
