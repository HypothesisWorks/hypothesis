RELEASE_TYPE: patch

This release improves the shrinker in cases where examples drawn earlier can
affect how much data is drawn later (e.g. when you draw a length parameter in
a composite and then draw that many elements). Examples found in cases like
this should now be much closer to minimal.
