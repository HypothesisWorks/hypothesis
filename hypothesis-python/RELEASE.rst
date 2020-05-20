RELEASE_TYPE: patch

This patch precomputes some of the setup logic for our experimental
:ref:`external fuzzer integration <fuzz_one_input>` and sets
:obj:`deadline=None <hypothesis.settings.deadline>` in fuzzing mode,
saving around 150us on each iteration.

This is around two-thirds the runtime to fuzz an empty test with
``@given(st.none())``, and nice to have even as a much smaller
fraction of the runtime for non-trivial tests.
