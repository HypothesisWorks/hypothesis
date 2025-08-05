RELEASE_TYPE: patch

Fixes a bug with solver-based :ref:`alternative backends <alternative-backends>` (like `crosshair <https://github.com/pschanely/CrossHair>`_) where symbolic values passed to |event| would not be realized to concrete values at the end of the test case.
