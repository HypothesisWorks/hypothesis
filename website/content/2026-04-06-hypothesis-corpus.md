---
date: 2026-04-06 00:00
title: The Hypothesis Corpus
authors: liam
---

<div class="cta-buttons">
  <a href="https://huggingface.co/datasets/HypothesisWorks/Hypothesis-Corpus-2026" class="cta-button">View the dataset</a>
</div>

Today, we're releasing the Hypothesis Corpus; a comprehensive dataset of 28,928 Hypothesis tests across 1,529 repositories.

Hypothesis is the most widely used property-based testing library in the world. This also makes it the largest source of real-world property-based tests anywhere. My goal in building and releasing this dataset is to provide valuable insights to us as Hypothesis developers, to property-based testing researchers, and to property-based testing maintainers across all languages, so we can all work together to make property-based testing better for everyone.

<img class="article__image" src="{static}/images/corpus_sankey.svg" alt="Sankey diagram of the repository filtering pipeline" />

The Hypothesis Corpus includes:

* Repository metadata.
* The source code of each test.
* The `@settings` configuration of each test.
* Runtime information for each test case, collected during test execution. Includes:
    * How long generating each sub-strategy took;
    * How much entropy was consumed during generation;
    * The test case outcome (passed, failed, filtered out, consumed too much entropy);
    * The value of any `assume()`, `.filter()`, `event()`, `note()`, or `target()` calls;
    * Line coverage;
    * Etc.
* And more.

If you're interested in more details about the dataset and our methodology, [please see our HuggingFace release](https://huggingface.co/datasets/HypothesisWorks/Hypothesis-Corpus-2026).

# Some interesting graphs

I set out to build this corpus with the goal of it being broadly interesting and useful, rather than having a specific question in mind. Here are some observations as I've looked through the data.

## Average lines exercised by a test

The number of lines of user code covered by the full run of a test is a rough proxy for how large of a "unit" of logic that test is scoped to.

<img class="article__image" src="{static}/images/corpus_unique_lines.svg" />

This shows a wide spread, with an average around 30 lines. This is about where I would have predicted.

Note the long tail of larger-scoped Hypothesis tests, indicating people often use a single Hypothesis tests to test entire programs, or large parts of programs.

## More complex test cases do not take longer to execute

Unsurprisingly, as the amount of entropy consumed by a test case increases—labeled in the data as `choices_size`—so does the time Hypothesis takes to generate it.

<img class="article__image" src="{static}/images/corpus_choices_generation.svg" />

However, the same is not true about *execution* time: test cases which consume more entropy tend to take about as long to run as those which consume less.

<img class="article__image" src="{static}/images/corpus_choices_execution.svg" />

This is a very surprising result! I don't quite know what to make of this one, and intend to investigate it further. This could have implications for how Hypothesis defines entropy, or for the kinds of code developers test with Hypothesis.

## Timing information

We tracked the time each test spends generating values from Hypothesis. This is very close to the total overhead Hypothesis adds to the test[^1], and so we'd like to keep this low relative to the total test runtime.

<img class="article__image" src="{static}/images/corpus_generation.svg" />

The spread here is high. Many tests spend almost no time in Hypothesis. Many tests spend more than half their time in Hypothesis. Be careful of drawing too many conclusions from this without factoring in absolute runtime: it's normal that a test whose body takes only 1ms to run spends most of its time inside Hypothesis.

Speaking of, here's the percentage of time a test spends in Hypothesis, vs its absolute runtime.

<img class="article__image" src="{static}/images/corpus_generation_vs_runtime.svg" />

We see a bimodal distribution. Tests with low percentage of time spent in Hypothesis run the full spectrum of total runtime, as do tests with high percentage of time spent in Hypothesis. Tests with middling time spent in Hypothesis rarely have high total runtime.

This makes intuitive sense to me: when there are only two factors to runtime (test runtime and Hypothesis runtime), if either factor gets into a bad performance case, that factor dominate the runtime almost no matter how long the other factor takes.

There are many more interesting relationships we can't go through in this blog post. If you're interested, I encourage you to check out the dataset.
# Conclusion

Hypothesis has been lucky enough to [be the subject of many research papers](https://hypothesis.readthedocs.io/en/latest/usage.html#research-papers-about-hypothesis) over the years. Zac, David, and I all have our share of academic experience, and we think that despite this there remains a rich set of research and relationships yet to be discovered in property-based testing.

We hope that releasing this dataset will foster not only that academic research, but the industry research that is often done first by practitioners like property-based testing maintainers.

If you're a researcher or property-based testing maintainer and want to chat about this dataset, feel free to reach out to me at `orionldevoe@gmail.com`.

[^1]: The only reason it's not equal is the very small overhead from `@given` and similar Hypothesis engine scaffolding.
