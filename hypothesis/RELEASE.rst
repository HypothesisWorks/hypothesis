RELEASE_TYPE: minor

This release adds |lowlevel|, a new namespace for "low level" APIs. |lowlevel| is intended for power uses of Hypothesis, and trades off ergonomics and safety for power and control.

To start, |lowlevel| contains the following new APIs:

- |weighted_booleans|, a low-level strategy that generates ``True`` with probability ``p``.
- |many|, a low-level utility for control over collection sizing.

``hypothesis.lowlevel`` is stable, but is subject to a slightly weaker policy than :ref:`our standard deprecation policy <deprecation-policy>`. ``hypothesis.lowevel`` is subject to the following deprecation policy:

* Breaking changes will be preceded by at least 3 months of a deprecation warning.
* After the 3 month period, breaking changes may occur during any of a patch, minor, or major release.
* Breaking changes may be made during a major release without the 3 month deprecation notice.
