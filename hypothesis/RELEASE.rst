RELEASE_TYPE: patch

This patch fixes an ``IndexError`` in the shrinker's ``reduce_each_alternative``
pass (:issue:`4977`): when re-randomising a test case to try a lower ``one_of``
branch, the new attempt can have fewer spans than the shrink target, and span
indices computed for the target were used unchecked against it. Such spans are
now skipped.
