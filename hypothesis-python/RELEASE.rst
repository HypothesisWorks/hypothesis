RELEASE_TYPE: patch

This changes Hypothesis to no longer import various test frameworks by default (if they are installed).
which will speed up the initial ``import hypothesis`` call.
