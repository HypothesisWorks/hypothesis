RELEASE_TYPE: patch

When :func:`~hypothesis.strategies.randoms` was called with `use_true_randoms=False`,
calling `sample` on it with an empty sequence and 0 elements would result in an error,
when it should have returned an empty sequence to agree with the normal behaviour of
`random.Random`. This fixes that discrepancy.

Fixes :issue:`3765``