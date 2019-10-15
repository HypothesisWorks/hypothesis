RELEASE_TYPE: minor

This release significantly simplifies Hypothesis's internal logic for data
generation, by removing a number of heuristics of questionable or unproven
value.

The results of this change will vary significantly from test to test. Most
test suites will see significantly faster data generation and lower memory
usage. The "quality" of the generated data may go up or down depending on your
particular test suites.

If you see any significant regressions in Hypothesis's ability to find bugs in
your code as a result of this release, please file an issue to let us know.
