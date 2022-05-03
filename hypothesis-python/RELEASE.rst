RELEASE_TYPE: patch

This patch fixes silently dropping examples when the :func:`@example <hypothesis.example>`
decorator is applied to itself (:issue:`3319`).  This was always a weird pattern, but now it
works.  Thanks to Ray Sogata, Keeri Tramm, and Kevin Khuong for working on this patch!
