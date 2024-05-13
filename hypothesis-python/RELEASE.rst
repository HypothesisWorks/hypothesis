RELEASE_TYPE: minor

This release improves our support for the :pypi:`annotated-types` iterable
``GroupedMetadata`` protocol.  In order to treat the elements "as if they
had been unpacked", if one such element is a :class:`~hypothesis.strategies.SearchStrategy`
we now resolve to that strategy.  Previously, we treated this as an unknown
filter predicate.

We expect this to be useful for libraries implementing custom metadata -
instead of requiring downstream integration, they can implement the protocol
and yield a lazily-created strategy.  Doing so only if Hypothesis is in
:obj:`sys.modules` gives powerful integration with no runtime overhead
or extra dependencies.
