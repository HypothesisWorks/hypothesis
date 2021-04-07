RELEASE_TYPE: patch

This patch teaches :command:`hypothesis write` to check for possible roundtrips
in several more cases, such as by looking for an inverse in the module which
defines the function to test.
