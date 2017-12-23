RELEASE_TYPE: patch

This release speeds up test case reduction in many examples by being better at
detecting large shrinks it can use to discard redundant parts of its input.
This will be particularly noticeable in examples that make use of filtering
and for some integer ranges.
