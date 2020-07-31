RELEASE_TYPE: patch

This release removes a number of Hypothesis's internal "shrink passes" - transformations
it makes to a generated test case during shrinking - which appeared to be redundant with
other transformations.

It is unlikely that you will see much impact from this. If you do, it will likely show up
as a change in shrinking performance (probably slower, maybe faster), or possibly in
worse shrunk results. If you encounter the latter, please let us know.
