RELEASE_TYPE: patch

This release changes how Hypothesis shrinks and replays examples to take into
account that it can encounter new bugs while shrinking. It now attempts to
identify whether the test failure is the same as the one it started with and
avoids shrinking into it (but still saves it for next time). This helps avoid
a phenomenon where rare bugs get shrunk into more common ones.
