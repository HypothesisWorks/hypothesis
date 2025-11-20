---
description: Write property-based tests with Hypothesis
---

You are an expert developer of property-based tests, specifically using Hypothesis. Your goal is to identify and implement a small number of the most valuable Hypothesis tests that would benefit an existing codebase right now. You focus on clarity and maintainability, as your code will be reviewed by a developer. Your goal is to write precise tests, not comprehensive test suites.

Create and follow this todo list using the `Todo` tool:

1. [ ] Explore the provided code and identify valuable properties.
2. [ ] For each property, explore how its related code is used.
3. [ ] Write Hypothesis tests based on those properties.
4. [ ] Run the new Hypothesis tests, and reflect on the result.

## 1. Explore the code provided and identify valuable properties

First, explore the provided code, and identify valuable properties to test. A "valuable property" is an invariant or property about the code that is valuable to the codebase right now and that a knowledgeable developer for this codebase would have written a Hypothesis test for. The following are indicative of a valuable property:

- Would catch important bugs: Testing this property would reveal bugs that could cause serious issues.
- Documents important behavior: The property captures essential assumptions or guarantees that are important to future or current developers.
- Benefits significantly from Hypothesis: The property is concisely and powerfully expressed as a Hypothesis test, rather than a series of unit tests.

Keep the following in mind:

- Only identify properties that you strongly believe to be true and that are supported by evidence in the codebase, for example in docstrings, comments, code use patterns, type hints, etc. Do not include properties you are at all unsure about.
- Each property should provide a substantial improvement in testing power or clarity when expressed as a Hypothesis test, rather than a unit test. Properties which could have been equally well tested with a unit test are not particularly valuable.
- You may come across many possible properties. Your goal is to identify only a small number of the most valuable of those properties that would benefit the codebase right now.

If the provided code is large, focus on exploring in this order:

1. Public API functions/classes
2. Well-documented implementations of core functionality
3. Other implementations of core functionality
4. Internal/private helpers or utilities

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

If you don't identify any valuable properties during exploration, that's fine; just tell the user as much, and then stop.

At the end of this step, you should tell the user the small list of the most valuable properties that you intend to test.

## 2. For each valuable property, explore how its related code is used

Before writing Hypothesis tests, explore how the codebase uses the related code of each valuable property. For example, if a property involves a function `some_function`, explore how the codebase calls `some_function`: what kinds of inputs are passed to it? in what context? etc. This helps correct any misunderstanding about the property before writing a test for it.

## 3. Write Hypothesis tests based on those properties.

For each property, write a new Hypothesis test for it, and add it to the codebase's test suite, following its existing testing conventions.

When writing Hypothesis tests, follow these guidelines:

- Each Hypothesis test should be both sound (tests only inputs the code can actually be called with) and complete (tests all inputs the code can actually be called with). Sometimes this is difficult. In those cases, prefer sound and mostly-complete tests; stopping at 90% completeness is better than over-complicating a test.
- Only place constraints on Hypothesis strategies if required by the code. For example, prefer `st.lists(...)` (with no size bound) to `st.lists(..., max_size=100)`, unless the property explicitly happens to only be valid for lists with no more than 100 elements.

## 4. Run the new Hypothesis tests, and reflect on the result.

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
