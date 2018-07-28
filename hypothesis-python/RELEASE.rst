RELEASE_TYPE: patch

This patch modifies how which rule to run is selected during 
:doc:`rule based stateful testing <stateful>`. This should result in a slight
performance increase during generation and a significant performance and
quality improvement when shrinking.

As a result of this change, some state machines which would previously have
thrown an ``InvalidDefinition`` are no longer detected as invalid.
