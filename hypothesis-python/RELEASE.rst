RELEASE_TYPE: minor

This Resolves a bug detailed (:issue:`2149`) where kwargs passed to Rule
were not being validated and consequently InvalidArgument errors were not being caught.

Thanks to Benjamin Palmer for this bugfix