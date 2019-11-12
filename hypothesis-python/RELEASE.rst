RELEASE_TYPE: patch

This patch avoids importing test runners such as :pypi`pytest`, :pypi`unittest2`,
or :pypi`nose` solely to access their special "skip test" exception types -
if the module is not in ``sys.modules``, the exception can't be raised anyway.

This fixes a problem where importing an otherwise unused module could cause
spurious errors due to import-time side effects (and possibly ``-Werror``).
