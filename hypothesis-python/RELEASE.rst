RELEASE_TYPE: patch

This patch teaches the :func:`~hypothesis.extra.ghostwriter.magic` ghostwriter
to recognise that pairs of functions like :func:`~python:colorsys.rgb_to_hsv`
and :func:`~python:colorsys.hsv_to_rgb` should
:func:`~hypothesis.extra.ghostwriter.roundtrip`.
