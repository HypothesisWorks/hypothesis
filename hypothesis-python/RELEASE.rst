RELEASE_TYPE: patch

This patch improves the implementation of an internal wrapper on Python 3.8
beta1 (and will break on the alphas; but they're not meant to be stable).
On other versions, there is no change at all.

Thanks to Daniel Hahler for the patch, and Victor Stinner for his work
on :bpo:`37032` that made it possible.
