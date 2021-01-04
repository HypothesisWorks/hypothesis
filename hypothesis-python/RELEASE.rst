RELEASE_TYPE: minor

This release upgrades :func:`~hypothesis.strategies.from_type`, to infer
strategies for type-annotated arguments even if they have defaults when
it otherwise falls back to :func:`~hypothesis.strategies.builds`
(:issue:`2708`).
