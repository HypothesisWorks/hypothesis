RELEASE_TYPE: minor

The |Phase.explain| phase now also varies interactive draws from |st.data|,
annotating each freely-variable ``Draw n: ...`` line with an
``# or any other generated value`` comment, just like |@given| arguments
(:issue:`4403`).

This release also fixes two explain-phase bugs: failing examples found just
as the set of possible inputs was fully enumerated were reported without
running the |Phase.shrink| and |Phase.explain| phases at all, and the
explain phase could fail to report that the commented parts can be varied
together if the failing example ended with an uncommented part.
