RELEASE_TYPE: minor

This release adds an ``allow_subnormal`` argument to the
:func:`~hypothesis.strategies.floats` strategy, which can explicitly toggle the
generation of :wikipedia:`subnormal floats <Subnormal_number>`. Disabling such
generation is useful when testing flush-to-zero builds of libraries, like is
typical with CuPy (:issue:`3155`).
