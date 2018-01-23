RELEASE_TYPE: patch

This release improves shrinking in a class of pathological examples that you
are probably never hitting in practice. If you *are* hitting them in practice
this should be a significant speed up in shrinking. If you are not, you are
very unlikely to notice any difference. You might see a slight slow down and/or
slightly better falsifying examples.
