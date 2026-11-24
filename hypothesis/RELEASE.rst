RELEASE_TYPE: patch

This patch fixes an ``IndexError`` in the shrinker's ``reduce_each_alternative``
pass, which could crash the ``target`` phase (:issue:`4977`). The span indices
used there are computed for the shrink target, but a re-randomised attempt can
have fewer spans, so the pass now skips span indices the attempt does not have.
