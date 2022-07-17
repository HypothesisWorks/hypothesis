RELEASE_TYPE: minor

This release adds the ``allow_subnormal`` argument to :func:`~hypothesis.strategies.complex_numbers` by
applying it to each of the real and imaginary parts separately. Closes :issue:`3390`.

Thanks to Evan Tey for this fix.
