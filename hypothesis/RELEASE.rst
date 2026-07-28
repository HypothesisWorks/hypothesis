RELEASE_TYPE: minor

The ``alphabet=`` argument of |st.from_regex| now accepts any collection of length-one strings, such as a tuple or list of characters (:issue:`4829`). This matches the existing behavior of |st.text|.
