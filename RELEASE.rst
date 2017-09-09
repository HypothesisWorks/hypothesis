RELEASE_TYPE: minor

This release changes how Hypothesis shrinks and replays examples to take into
account that it can encounter new bugs while shrinking the bug it originally
found. Previously it would end up replacing the originally found bug with the
new bug and show you only that one. Now it is (often) able to recognise when
two bugs are distinct and when it finds more than one will show both.
