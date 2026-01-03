RELEASE_TYPE: patch

This patch fixes :func:`~hypothesis.strategies.from_type` to properly handle
parameterized type aliases created with Python 3.12+'s :pep:`695` ``type``
statement. For example, ``st.from_type(A[int])`` where ``type A[T] = list[T]``
now correctly resolves to ``lists(integers())`` instead of raising a
``TypeError`` (:issue:`4628`).
