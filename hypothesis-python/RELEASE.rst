RELEASE_TYPE: minor

This release fixes some cases where we might previously have failed to run the
validation logic for some strategies. As a result tests which would previously
have been silently testing significantly less than they should may now start
to raise ``InvalidArgument`` now that these errors are caught.
