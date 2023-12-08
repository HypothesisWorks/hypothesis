RELEASE_TYPE: patch

This patch fixes an issue where :func:`~hypothesis.strategies.builds` could not be used with :pypi:`attrs` objects that defined private attributes (i.e. attributes with a leading underscore). See also :issue:`3791`.

This patch also adds support more generally for using :func:`~hypothesis.strategies.builds` with attrs' ``alias`` parameter, which was previously unsupported.

This patch increases the minimum required version of attrs to 22.2.0.
