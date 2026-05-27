---
date: 2025-11-16 00:01
title: Introducing HypoFuzz
authors: liam, zac-hd
---

If you're reading this blog, you probably know and hopefully love Hypothesis - we've been helping users write better test functions for over a decade now, which you can run with `pytest`, or `unittest`, or any other way you can call a Python function.

Getting called just like a traditional unit test is great for interactive development and for CI, but those aren't the only great workflows.  What if you could get much more out of your existing tests, with no new work?

**That's why we've built [HypoFuzz](https://hypofuzz.com/), which you can use today to find deep bugs and understand your tests**.

<div class="cta-buttons">
  <a href="https://hypofuzz.com/docs/quickstart.html" class="cta-button">Quickstart</a>
  <a href="https://hypofuzz.com/example-dashboard/" class="cta-button">Online demo</a>
</div>


# Dream workflows

Nelson Elhage writes about [two kinds of testing](https://blog.nelhage.com/post/two-kinds-of-testing/): *finding bugs* vs. *catching regressions*.  (and also [about PBT and fuzzing](https://blog.nelhage.com/post/property-testing-like-afl/))
To find bugs, you'd want to generate as many random inputs as possible; to catch regressions you'd want a fast and deterministic test suite.

Hypothesis can be configured to serve each of these roles, with the `phases=` setting, and database or `@example()` decorator making it easy to move valuable test cases found during the slow and random search into a fast deterministic configuration.  This is in fact how CPython uses Hypothesis: in most configurations, their tests *only* run the `@example` cases; and then there are separate CI workers which use the same tests to search for new failing inputs.

HypoFuzz lets you push this even further: you can dedicate a server to looking for interesting inputs - whether failing, or just covering some under-tested behavior.  We usually give dev machines read-only access to the fuzzing database, so that any failures can be reproduced simply by running the tests locally, but keep CI machines more isolated to avoid blocking work in flight when latent bugs are eventually discovered.


# Finding deeper bugs

When it comes to finding deep bugs, HypoFuzz has several advantages over Hypothesis - even if you're running them for the same length of time.  These are due to either solving a different problem, or using heuristics and techniques which pay off in longer runs but have too much overhead to use in an interactive or CI-style workflow.

HypoFuzz uses a more expensive, more powerful approach to input generation, organized around coverage-guided fuzzing.  At a high level, we record the code coverage from each input, and can generate new inputs either from scratch, or as variations on a previously generated input.  This is particularly useful because once we discover how to trigger rare behavior, we can search that area until the behavior is no longer rare.  Even our earliest, very basic implementations of this approach found novel bugs in `hypothesis-jsonschema` which Hypothesis had missed for hundreds of hours.

HypoFuzz also dynamically optimizes the allocation of search time *between* test functions, to maximize the overall bug discovery rate.  Tests for very simple code can "saturate" relatively quickly; and as they do we'll spend more and more runtime on the remaining tests where more coverage (and bugs) remain to be found.  This also allows us to flexibly autoscale the whole system, so you can run HypoFuzz on anything from your laptop, to a dedicated server, to a pool of spot instances or fragments of idle CPU.

<img src="{static}/images/hypofuzz_dashboard.png" alt="HypoFuzz dashboard" style="max-width: 100%;" />

Check out [our literature review](https://hypofuzz.com/docs/literature.html) to read more about these techniques!


# Understand your tests

Ever written a test and been suspicious when it passes first-try? The dashboard shows input distributions and lets you inspect individual test cases. For particularly interesting tests, you can add custom events for HypoFuzz to graph.

<img src="{static}/images/hypofuzz_observability.webp" alt="HypoFuzz observability" style="max-width: 100%;" />

[The Tyche vscode extension](https://marketplace.visualstudio.com/items?itemName=HarrisonGoldstein.tyche) gives you similar feedback live in your editor, while the HypoFuzz dashboard can collect, store, and analyze a larger volume of data - including from other machines.  We recommend both :-)


# Why not open source?

We love open source as much as anyone else, and have spent full-time-years worth of work maintaining and improving Hypothesis for free.  It's great to hear from middle-schoolers, open-source maintainers, researchers, hobbyists, and professional engineers using Hypothesis, and Hypothesis itself will remain open-source forever.  Non-commercial use of HypoFuzz is completely free, too--the more people who can build ambitious things with the confidence fuzzing brings, the happier we'll be.

The pitch for *HypoFuzz* though is that we can offer a way to turn money spent on compute into discovered bugs - and we think it's fair for businesses who spend money running HypoFuzz to pay some of that money to us, not just their cloud provider.

Finally... if we could pay the bills by working on Hypothesis and HypoFuzz, we'd both have a lot of fun and advance the state of the art a lot faster!  The low-hanging fruit is long gone from [our issue tracker](https://github.com/HypothesisWorks/hypothesis/issues), and the remaining issues are often pretty gnarly or require deep enough context that external contributors are rare.


# Call to fuzzing!

* **[Start using HypoFuzz](https://hypofuzz.com/docs/quickstart.html)**: it's free for non-commercial use, and businesses can [get in touch](mailto:sales@hypofuzz.com?subject=Evaluation%20HypoFuzz%20licence) for a no-cost evaluation license.
* **We want to hear from you**, so we can help make HypoFuzz work for you: [get in touch](mailto:hello@hypofuzz.com?subject=HypoFuzz) or [book a chat](https://calendar.app.google/XDBzPvxbLaP2tQLE8) to tell us what you want to see in HypoFuzz, or in general fuzzing / PBT workflows!
