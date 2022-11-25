RELEASE_TYPE: patch

This patch shifts ``hypothesis[lark]`` from depending on the old :pypi:`lark-parser`
package to the new :pypi:`lark` package.  There are no code changes in Hypothesis,
it's just that Lark got a new name on PyPI for version 1.0 onwards.
