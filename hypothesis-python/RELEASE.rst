RELEASE_TYPE: patch

This release adds a new random exploration phase to shrinking. Surprisingly, this
should make the output more deterministic! As a result of this new phase many
bugs which previously would sometimes get a variety of different falsifying examples
reported (if you were running without the example database) should now more reliably
get the same output each time.
