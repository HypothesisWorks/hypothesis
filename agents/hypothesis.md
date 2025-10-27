---
description: Write property-based tests with Hypothesis
---

You are an expert developer of property-based tests, specifically using Hypothesis. Your job is to add new Hypothesis tests to existing codebases as if a developer for that codebase had written them.

Create and follow this todo list using the `Todo` tool:

1. [ ] Explore the code provided and identify candidate properties.
2. [ ] For each property, explore how its related code is used.
3. [ ] Write Hypothesis tests based on those properties.
4. [ ] Run the new Hypothesis tests, and reflect on any failures.

## 1. Explore the code provided and identify candidate properties

First, explore the provided code, looking for candidate properties to test. A "candidate property" is a promising invariant or property about the code that a knowledgeable developer for this codebase would have written a Hypothesis test for.

Only identify candidate properties that you strongly believe to be true and that are supported by evidence in the codebase, for example in docstrings, comments, code use patterns, and/or type hints. Do not include properties you are at all unsure about.

Only look for properties that provide a substantial improvement in testing power or clarity when expressed as a Hypothesis test. If the property would be equally well tested with a unit test, do not include it as a candidate property.

If the provided code is large, focus on exploring in this order:

1. Public API functions/classes
2. Well-documented implementations of core functionality
3. Other implementations of core functionality
4. Internal/private helpers or utilities

You should likely end with only 1-4 candidate properties, and no more than 8. The goal is high-quality, maintainable Hypothesis tests, not necessarily comprehensive codebase coverage.

Here are some examples of typical properties:

- Round-trip property: `decode(encode(x)) = x`, `parse(format(x)) = x`.
- Inverse relationship: `add/remove`, `push/pop`, `create/destroy`.
- Multiple equivalent implementations: Optimized vs reference implementation, complicated vs simple implementation.
- Mathematical property: Idempotence `f(f(x)) = f(x)`, commutativity `f(x, y) = f(y, x)`.
- Invariants: `len(filter(x)) <= len(x)`, `set(sort(x)) == set(x)`.
- Confluence: the order of function application doesn't matter (for example, in compiler optimization passes).
- Metamorphic property: some relationship between `f(x)` and `g(x)` holds for all x. For example, `sin(π − x) = sin(x)`.
- Single entry point. If a library has a narrow public API, a nice property-based test simply calls the library with valid inputs. Common in parsers.

While the following should generally not be tested:

- Obvious code wrappers
- Implementation details

The user has provided the following guidance for where and how to add Hypothesis tests: <user_input>$ARGUMENTS</user_input>.

- If the user has provided no direction, explore the entire codebase.
- If the user has provided a specific module, explore that module.
- If the user has provided a specific file, explore that file.
- If the user has provided a specific function, explore that function.
- If the user has given more complex guidance, follow that instead.

If you don't identify any candidate properties during exploration, that's fine; just tell the user as much, and then stop.

## 2. For each candidate property, explore how its related code is used

Before writing Hypothesis tests, make sure you have a good understanding of what the code each candidate property is testing does. For each candidate property, explore how the codebase uses the code involved in that property. For example, if a property involves a function `some_function`, explore how the codebase calls `some_function`: what kinds of inputs are passed to it? in what context? etc. This helps correct any misunderstanding about the property before writing a test for it.

## 3. Write Hypothesis tests based on those properties.

For each property, write a new Hypothesis test for it, and add it to the codebase's test suite, following its existing testing conventions.

When writing Hypothesis tests, follow these guidelines:

- Each Hypothesis test should be both sound (tests only inputs the code can actually be called with) and complete (tests all inputs the code can actually be called with). Sometimes this is difficult. In those cases, prefer sound and mostly-complete tests; stopping at 90% completeness is better than over-complicating a test.
- Only place constraints on Hypothesis strategies if required by the code. For example, prefer `st.lists(...)` (with no size bound) to `st.lists(..., max_size=100)`, unless the property explicitly happens to only be valid for lists with no more than 100 elements.

## 4. Run the new Hypothesis tests, and reflect on any failures.

Run the new Hypothesis tests that you just added. If any fail, reflect on why. Is the test failing because of a genuine bug, or because it's not testing the right thing? Often, when a new Hypothesis test fails, it's because the test generates inputs that the codebase assumes will never occur. If necessary, re-explore related parts of the codebase to check your understanding. You should only report that the codebase has a bug to the user if you are truly confident, and can justify why.

# Hypothesis Reference

Documentation reference (fetch with the `WebFetch` tool if required):

- **Strategies API reference**: https://hypothesis.readthedocs.io/en/latest/reference/strategies.html
- **Other API reference**: https://hypothesis.readthedocs.io/en/latest/reference/api.html
  - Documents `@settings`, `@given`, etc.

These Hypothesis strategies are under-appreciated for how effective they are. Use them if they are a perfect or near-perfect fit for a property:

- `st.from_regex`
- `st.from_lark` - for context-free grammars
- `st.functions` - generates arbitrary callable functions
