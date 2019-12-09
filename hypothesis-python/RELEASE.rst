RELEASE_TYPE: patch

This release reorganises a number of the Hypothesis internal modules into a
package structure. If you are only depending on the public API it should have
no effect. If you are depending on the internal API (which you shouldn't be,
and which we don't guarantee compatibility on) you may have to rename some
imports.
