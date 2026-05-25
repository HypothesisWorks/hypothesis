RELEASE_TYPE: patch

When Hypothesis detects that your data generation is flaky and raises
``FlakyStrategyDefinition``, the error message now describes *what* differed
between the two runs - such as a different choice type, different constraints,
or drawing more or less data - as well as the stack of strategies being drawn
from, instead of only reporting that generation was inconsistent.

Thanks to Ian Hunt-Isaak for this improvement!
