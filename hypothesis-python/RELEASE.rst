RELEASE_TYPE: patch

This patch restores compatibility when using `the legacy Python 3.9 LL(1)
parser <https://docs.python.org/3/whatsnew/3.9.html#new-parser>`__ yet
again, because the fix in :ref:`version 6.131.33 <v6.131.33>` was too
brittle.

Thanks to Marco Ricci for this fix!
