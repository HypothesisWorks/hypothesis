RELEASE_TYPE: patch

This release improves the output of failures with
:ref:`rule based stateful testing <rulebasedstateful>` in two ways:

* The output from it is now usually valid Python code.
* When the same value has two different names because it belongs to two different
  bundles, it will now display with the name associated with the correct bundle
  for a rule argument where it is used.
