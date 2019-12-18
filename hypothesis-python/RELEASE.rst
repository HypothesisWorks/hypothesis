RELEASE_TYPE: patch

This release makes Hypothesis better at generating test cases where generated
values are duplicated in different parts of the test case. This will be
especially noticeable with reasonably complex values, as it was already able
to do this for simpler ones such as integers or floats.
