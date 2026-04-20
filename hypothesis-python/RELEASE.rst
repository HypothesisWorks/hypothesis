RELEASE_TYPE: patch

Simplify our internal ``next_up`` and ``next_down`` helpers by delegating to
:func:`math.nextafter` (:issue:`4710`).
