RELEASE_TYPE: patch

This patch improves shrinking of floats larger than ``2**53``, where the gap
between adjacent floats exceeds one and the previous integer-based shrinker
could stall.  Such floats now shrink on the float grid directly, often turning
hundreds of internal test calls into a handful.
