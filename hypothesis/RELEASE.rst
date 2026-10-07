RELEASE_TYPE: patch

:ref:`The Ghostwriter <ghostwriter>` now raises a helpful error for functions
which take no arguments, instead of writing a test with an invalid empty
``@given()`` decorator (:issue:`4882`).

Thanks to deepak7lal for this fix!
