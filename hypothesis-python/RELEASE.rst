RELEASE_TYPE: patch

This patch fixes a bug since :ref:`v6.99.13` where only interactively-generated values (via ``data.draw``) would be reported in the ``arguments`` field of our :doc:`observability output <observability>`. Now, all values are reported.
