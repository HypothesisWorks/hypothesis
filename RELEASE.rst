RELEASE_TYPE: patch

This release improves the behaviour of  :doc:`stateful testing <stateful>`
in two ways:

* Previously some runs would run no steps (:issue:`376`). This should no longer
  happen.
* RuleBasedStateMachine tests which used bundles extensively would often shrink
  terribly. This should now be significantly improved, though there is likely
  a lot more room for improvement.

This release also involves a low level change to how ranges of integers are
handles which may result in other improvements to shrink quality in some cases.
