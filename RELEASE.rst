RELEASE_TYPE: patch

This is a refactoring release. It moves a number of internal uses
of nametuple over to using attrs based classes, and removes a couple
of internal namedtuple classes that were no longer in use.


It should have no user visible impact.
