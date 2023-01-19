RELEASE_TYPE: patch

This patch fixes missing imports of the :mod:`re` module, when :doc:`ghostwriting <ghostwriter>`
tests which include compiled patterns or regex flags.
Thanks to Jens Heinrich for reporting and promptly fixing this bug!