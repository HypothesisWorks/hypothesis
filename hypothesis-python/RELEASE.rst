RELEASE_TYPE: patch

The ``hypothesis-urandom`` :ref:`backend <alternative-backends>` now reads from ``/dev/urandom`` with buffering disabled, which improves the control of those hooking ``/dev/urandom`` to change or read Hypothesis's random decisions.
