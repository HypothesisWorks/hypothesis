RELEASE_TYPE: patch

This release fixes an internal issue where Hypothesis would sometimes generate
test cases that were above its intended maximum size. This would only have
happened rarely and probably would not have caused major problems when it did.

Users of the new  :ref:`targeted property-based testing <targeted-search>` might
see minor impact (possibly slightly faster tests and slightly worse target scores),
but only in the unlikely event that they were hitting this problem. Other users
should not see any effect at all.
