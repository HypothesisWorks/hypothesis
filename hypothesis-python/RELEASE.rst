RELEASE_TYPE: minor

Calling :func:`~hypothesis.settings.register_profile` from within a test
decorated with :func:`@settings <hypothesis.settings>` is now deprecated,
to avoid confusion about which settings are used as the baseline for the
new profile.
