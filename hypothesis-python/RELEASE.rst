RELEASE_TYPE: minor

This changes the behaviour of settings profiles so that if you reregister the currently loaded profile it will automatically reload it. Previously you would have had to load it again.

In particular this means that if you register a "ci" profile, it will automatically be used when Hypothesis detects you are running on CI.
