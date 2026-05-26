RELEASE_TYPE: minor

|event|'s ``payload`` is now typed as accepting |Any|, matching its runtime behavior of accepting any string-coercible object.

When Hypothesis detects that your data generation is flaky and raises
|FlakyStrategyDefinition|, the error message now describes *what* differed
between the two runs - such as a different choice type, different constraints,
or drawing more or less data - as well as the stack of strategies being drawn
from, instead of only reporting that generation was inconsistent. In stateful
tests, it also reports the steps leading up to the error.

Thanks to Ian Hunt-Isaak for this improvement!
