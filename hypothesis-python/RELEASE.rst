RELEASE_TYPE: patch

Fixes a rare internal error where new code from :ref:`version 6.131.1 <v6.131.1>`
could fail if :py:data:`sys.modules` is simultaneously modified, e.g. as a side
effect of imports executed from another thread.  Our :ref:`thread-safety-policy`
does not promise that this is supported, but we're happy to take reasonable
fixes.

Thanks to Tony Li for reporting and fixing this issue.
