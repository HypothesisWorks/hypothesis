RELEASE_TYPE: patch

This patch restores compatibility when using `the legacy Python 3.9 LL(1)
parser <https://docs.python.org/3/whatsnew/3.9.html#new-parser>`__, which
was accidentally broken since :ref:`version 6.130.13 <v6.130.13>`.

Thanks to Marco Ricci for this fix!
