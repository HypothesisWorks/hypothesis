RELEASE_TYPE: patch

This patch fixes a bug in ``compute_max_children`` and ``all_children`` where
NaN values were not accounted for when ``allow_nan=True``. This could prevent
float branches from being marked as exhausted, cause unnecessary force-splits
of single-value float nodes, and prevent the cache-based drawing path from
producing NaN values.

This patch also fixes a bug in ``choice_constraints_key`` where integer
``weights`` values were not included in the constraints key. Only the weight
keys were hashed, so ``{5: 0.99}`` and ``{5: 0.01}`` produced the same key,
causing the constraints cache to return the wrong weights and ``ChoiceNode``
equality to incorrectly equate nodes with different weight values.

This patch also fixes a bug in ``_pop_choice`` where a ``forced`` value was
ignored when the prefix contained a ``ChoiceTemplate``. The ``forced`` value
was set but then immediately overwritten by ``choice_from_index(0, ...)``,
which could raise ``ChoiceTooLarge`` for bytes/string choices with large
``min_size``, causing an unnecessary overrun even though a valid forced value
was available.

This patch also fixes four bugs in ``BytestringProvider``:

- ``draw_integer`` could not generate negative values when ``min_value`` was
  negative, because ``_draw_bits`` always returns a non-negative integer. For
  ranges where both ``min_value`` and ``max_value`` were negative, this caused
  an infinite loop leading to an overrun error.
- ``draw_string`` with an empty ``IntervalSet`` caused an overrun error
  because it attempted to draw integers from an empty range, instead of
  returning an empty string like ``HypothesisProvider``.
- ``draw_boolean`` with very small ``p`` (e.g. ``1e-99``) could never return
  ``True``, because the ``falsey`` threshold was not capped at ``size - 1``,
  contradicting the code's own comment that at least one value should be true.

This patch also fixes a bug in ``make_float_clamper`` where resampling
out-of-bounds floats with infinite ``min_value`` or ``max_value`` always
produced an infinite result, bypassing the ``smallest_nonzero_magnitude``
correction. This meant that disallowed floats (e.g. NaN when
``allow_nan=False``, or subnormal floats below
``smallest_nonzero_magnitude``) were clamped to ``-inf`` instead of a valid
in-bounds value.

This patch also fixes a bug where the observability ``status_reason`` was
empty for ``gave_up`` test cases when using the ``crosshair`` backend. The
``reason`` on the ``UnsatisfiedAssumption`` raised by ``assume()`` could be
corrupted to an empty string by crosshair's opcode tracing when the f-string
was evaluated inline in the raising frame; it is now computed in a helper
frame, like the other message components.
