RELEASE_TYPE: patch

This patch tightens up some of our internal heuristics to deal with shrinking floating point numbers,
which will now run in fewer circumstances.

You are fairly unlikely to see much difference from this, but if you do you are likely to see shrinking become slightly faster and/or producing slightly worse results.
