RELEASE_TYPE: patch

This release extends Hypothesis's multiple bug discovery functionality to be
able to find multiple bugs during test case generation. It will now not stop
generating on the first bug, but will continue generating for a little while
(not necessarily the full number of examples it would have run if it hadn't
found a bug) and see if it discovers any new bugs.
