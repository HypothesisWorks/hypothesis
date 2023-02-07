RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.complex_numbers` accidentally
invalidating itself when passed magnitude arguments for 32 and 64-bit widths,
due to not internally down-casting numbers (:issue:`3573`).
