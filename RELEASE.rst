RELEASE_TYPE: patch

This release improves the behaviour of  :doc:`stateful testing <stateful>`
in two ways:

* Previously some runs would run no steps (:issue:`376`). This should no longer
  happen.
* RuleBasedStateMachine tests which used bundles extensively would often shrink
  terribly. This should now be significantly improved, though there is likely
  a lot more room for improvement.
