RELEASE_TYPE: minor

Hypothesis has historically referred to the single execution of a test function as an "example". However, we have in recent years tended to call a single execution a "test case" instead, which we think is a more precise and less overloaded term.

This release updates user-facing documentation, log messages, and error messages to use the "test case" terminology.

This is not a breaking change, as we have intentionally not changed any code APIs. For example, |settings.max_examples| has not been changed.
