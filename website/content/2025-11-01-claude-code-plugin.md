---
date: 2025-11-01 00:00
title: A Claude Code command for Hypothesis
author: Liam DeVoe, Muhammad Maaz, Zac Hatfield-Dodds, Nicholas Carlini
---

<div class="cta-buttons">
  <a href="https://github.com/HypothesisWorks/hypothesis/blob/master/.claude/commands/hypothesis.md" class="cta-button">
    <img src="/theme/icon-code.svg" alt="" class="cta-icon">
    View the command
  </a>
  <a href="https://mmaaz-git.github.io/agentic-pbt-site/" class="cta-button">
    <img src="/theme/icon-paper.svg" alt="" class="cta-icon">
    Read the paper
  </a>
</div>

*We wrote a paper using Claude to autonomously write and run Hypothesis tests, and found real bugs in numpy, pandas, and other packages. We've extracted this to a Claude Code command for writing Hypothesis tests, which we're sharing today. We hope you find it useful.*

*(Not familiar with property-based testing? [Learn more here](https://increment.com/testing/in-praise-of-property-based-testing/)).*

---

Hypothesis has shipped with [the ghostwriter](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html#ghostwriter) for quite a while, which automatically writes Hypothesis tests for your code. It uses nothing but good old fashioned heuristics, and is a nice way to stand up Hypothesis tests with minimal effort.

Recently, we explored what this same idea might look like with modern AI tools, like Anthropic's Claude Sonnet 4.5 and OpenAI's GPT-5, and the results have been pretty compelling. So we're happy to release `/hypothesis`, a [Claude Code](https://www.claude.com/product/claude-code) command that we developed to automate writing Hypothesis tests.

The `/hypothesis` command instructs the model to automatically read your code, infer testable properties, and add Hypothesis tests to your test suite. The idea is that if you wanted to add Hypothesis tests for a file `mypackage/a/utils.py`, you could run `/hypothesis mypackage/a/utils.py`, go get a coffee, and then come back to see some new newly-added tests. You can alternatively give more complex instructions, like `/hypothesis focus on the database implementation; add tests to test_db.py`.

We've found `/hypothesis` pretty useful when combined with modern AI models, for tasks ranging from setting up tests in fresh repositories, to augmenting existing test suites, to standing up a full fuzzing workflow with [HypoFuzz](https://hypofuzz.com/).

Since `/hypothesis` doesn't (yet) make sense to release in Hypothesis itself, we're releasing it here. [You can find the full command here](https://github.com/HypothesisWorks/hypothesis/blob/master/.claude/commands/hypothesis.md), install it by copying into `~/.claude/commands/`, and run it with `/hypothesis` inside of Claude Code[^1].

# Designing the `/hypothesis` command

The broad goal of the `/hypothesis` command is to: (1) look at some code; (2) discover properties that make sense to test; and (3) write Hypothesis tests for those properties.

As many developers will attest, often the trickiest part of property-based testing is figuring out what property to test. This is true for modern AI models as well. We therefore design the instructions of `/hypothesis` around gathering as much context about potential properties as it can, before writing any tests. This ensures that the tests the model writes are strongly supported by factual evidence, for example in type hints, docstrings, usage patterns, or existing unit tests.

The flow of the `/hypothesis` instructions looks like this:

1. Explore the provided code and identify candidate properties.
2. Explore how the codebases calls that code in practice.
3. Grounded in this understanding, write corresponding Hypothesis tests.
4. Run the new Hypothesis tests, and reflect on any failures. Is it a genuine bug, or is the test incorrect? Refactor the test if necessary.

The legwork that `/hypothesis` instructs the model to do both before and after writing a test is critical for deriving high-quality tests. For example, the model might discover in step 2 that a function is called with two different input formats, and both should be tested. Or it might discover in step 4 that it wrote an unsound test, by generating test inputs the function didn't expect, like `math.nan`.

## Failure modes

We observed a few failure modes while developing `/hypothesis`. For example, AI models like to write strategies with unnecessary restrictions, like limiting the maximum length of a list even when the property should hold for all lengths of lists. We added explicit instructions in `/hypothesis` not to do this, though that doesn't appear to have fixed the problem entirely.

By far the most fundamental failure mode is that the model might simply misunderstand a property in the code. For example, we ran `/hypothesis` on [python-dateutil](https://github.com/dateutil/dateutil); specifically, `/hypothesis src/easter.py`. The model determined that a property of the `easter` function is that it should always return a date on a Sunday, no matter the `method` argument, of which dateutil provides three: `method=EASTER_JULIAN`, `method=EASTER_ORTHODOX`, `method=EASTER_WESTERN`. The model wrote a test saying as much, which then failed, and it proudly claimed it had found a bug.

In fact, the model had not found a bug. In reality, `dateutil.easter` computes the date for Easter in the calendar corresponding to the passed `method`, but always returns that date in the Gregorian calendar—which might not be a Sunday. The test written by the model assumed the computation occurred in the Gregorian calendar from start to finish, which was incorrect.

This kind of subtle semantic reasoning remains difficult for models, and it's important to keep it in mind as a limitation.

# Using `/hypothesis` for bug hunting

Armed with a test-writing command, one natural extension is to use it to find real bugs in open-source repositories. To explore this, we used Claude Opus 4.1 to automatically write and run Hypothesis tests for a number of popular Python packages. The results were promising—we found bugs in NumPy, pandas, and Google and Amazon SDKs, and [submitted](https://github.com/numpy/numpy/pull/29609) [patches](https://github.com/aws-powertools/powertools-lambda-python/pull/7246) [for](https://github.com/aws-cloudformation/cloudformation-cli/pull/1106) [several](https://github.com/huggingface/tokenizers/pull/1853) of them. You can [read more in our paper](https://mmaaz-git.github.io/agentic-pbt-site/); it's quite short, so do give it a read if you're interested.

It's insightful to walk through one bug we found in particular: a bug in [NumPy's `numpy.random.wald`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.wald.html) function (also called the inverse Gaussian distribution).

To start, we ran `/hypothesis numpy.random` to kick off the model. This directs the model to write tests for the entire `numpy.random` module. The model starts by reading the source code of `numpy.random` as well as any relevant docstrings. It sees the function `wald`, realizes from its background knowledge that the mathematical `wald` function should only produce positive values, and tracks that as a potential property. It reads further and discovers from the docstring of `wald` that both the `mean` and `scale` parameters must be greater than 0.

Based on this understanding, and a few details from docstrings that we've omitted, the model proposes a range of properties:

1. All outputs of `wald` are positive.
2. No `math.nan` or `math.inf` values are returned on valid inputs.
3. The returned array shape matches the `size` parameter.
4. The `mean` and `scale` arrays broadcasts correctly.
5. Seeding the distribution produces deterministic results.

And then goes about writing Hypothesis tests for them. Here's one of the (slightly formatted) tests it writes:

```python
import numpy as np

from hypothesis import given, strategies as st

positive_floats = st.floats(
    min_value=1e-10, max_value=1e6, allow_nan=False, allow_infinity=False
)


@given(
    mean=positive_floats,
    scale=positive_floats,
    size=st.integers(min_value=1, max_value=1000),
)
def test_wald_all_outputs_positive(mean, scale, size):
    """Test that all Wald distribution samples are positive."""
    samples = np.random.wald(mean, scale, size)
    assert np.all(samples > 0), f"Found non-positive values: {samples[samples <= 0]}"
```

It then runs this test. And the test fails! After reflection, the model decides this is a real bug, leaves the test in the test suite, and reports the failure to the developer.

What's going on here? We tracked this bug down to catastrophic cancellation in NumPy's `wald` implementation, which could sometimes result in negative values. We reported this to the NumPy maintainers alongside a patch with a more numerically stable algorithm. The NumPy maintainers confirmed the bug, and our fix was released in [v2.3.4](https://github.com/numpy/numpy/releases/tag/v2.3.4). You can [check out the PR here](https://github.com/numpy/numpy/pull/29609).

We think this is a really neat confirmation of both the power of property-based testing, and the ability of current AI models to reason about code.

# Conclusion

We hope you find `/hypothesis` useful in adding Hypothesis tests to your test suites! Developing AI prompts is more of an art than a science; so we encourage you to give any feedback on `/hypothesis` by [opening an issue in the Hypothesis repository](https://github.com/HypothesisWorks/hypothesis/issues/new), even if it's just some open-ended thoughts.

[^1]: While Claude Code is currently the most popular tool that supports custom commands, `/hypothesis` is just a markdown file, and works equally as well with any AI framework that supports commands.
