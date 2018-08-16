RELEASE_TYPE: patch

This change fixes a small bug in how the core engine caches the results of
previously-tried inputs. The effect is unlikely to be noticeable, but it might
avoid unnecesary work in some cases.
