RELEASE_TYPE: patch

This patch improves our pretty-printer (:issue:`4037`).

It also fixes the codemod for ``HealthCheck.all()`` from
:ref:`version 6.72 <v6.72.0>`, which was instead trying to
fix ``Healthcheck.all()`` - note the lower-case ``c``!
Since our tests had the same typo, it all looked good...
until :issue:`4030`.
