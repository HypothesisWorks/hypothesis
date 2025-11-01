RELEASE_TYPE: minor

Hypothesis previously required :pypi:`attrs` as a dependency. This release removes that dependency, so that the only required dependency of Hypothesis is :pypi:`sortedcontainers`.

All attrs-specific features of Hypothesis, such as using |st.from_type| with attrs classes, will continue to behave as before.
