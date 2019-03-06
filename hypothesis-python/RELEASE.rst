RELEASE_TYPE: minor

This release significantly tightens validation in :class:`hypothesis.settings`.
:obj:`~hypothesis.settings.max_examples`, :obj:`~hypothesis.settings.buffer_size`,
and :obj:`~hypothesis.settings.stateful_step_count` must be positive integers;
:obj:`~hypothesis.settings.deadline` must be a positive number or ``None``; and
:obj:`~hypothesis.settings.derandomize` must be either ``True`` or ``False``.

As usual, this replaces existing errors with a more helpful error and starts new
validation checks as deprecation warnings.
