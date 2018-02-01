RELEASE_TYPE: patch

This release changes the way in which Hypothesis tries to shrink the size of
examples. It probably won't have much impact, but might make shrinking faster
in some cases. It is unlikely but not impossible that it will change the
resulting examples.
