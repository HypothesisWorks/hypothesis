RELEASE_TYPE: minor

Changes the distribution of :func:`~hypothesis.strategies.sampled_from` when
sampling from a :func:`~python:enum.Flag`. Previously, no-flags-set values would
never be generated, and all-flags-set values would be unlikely for large enums.
With this change, the distribution is more uniform in the number of flags set.
