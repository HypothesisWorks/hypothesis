RELEASE_TYPE: minor

The |Phase.explain| phase now also varies interactive draws from |st.data|,
annotating each freely-variable ``Draw n: ...`` line with an
``# or any other generated value`` comment, just like |@given| arguments
(:issue:`4403`).

This release also fixes a bug where the explain phase could fail to report
that the commented parts can be varied together, if the failing example
ended with an uncommented part.
