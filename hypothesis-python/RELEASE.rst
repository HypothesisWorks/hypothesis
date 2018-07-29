RELEASE_TYPE: patch

This release fixes a bug that could cause an ``IndexError`` to be raised from
inside Hypothesis during shrinking. It is likely that it was impossible to
trigger this bug in practice - it was only made visible by some currently
unreleased work.
