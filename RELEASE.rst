RELEASE_TYPE: patch

This patch fixes our tests for Numpy dtype strategies on big-endian platforms,
where the strategy behaved correctly but the test assumed that the native byte
order was little-endian.

There is no user impact unless you are running our test suite on big-endian
platforms.  Thanks to Graham Inggs for reporting :issue:`1164`.
