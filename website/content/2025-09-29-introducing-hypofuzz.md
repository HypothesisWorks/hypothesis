---
date: 2025-08-07 00:00
title: Introducing HypoFuzz
author: Liam & Zac
---

**TL;DR:** [HypoFuzz](https://hypofuzz.com/) is a fuzzing backend and dashboard for your Hypothesis tests. It's designed for deep bug discovery, observability, and autoscaling, and effortlessly combines property-based testing and fuzzing. [Try it today](https://hypofuzz.com/docs/quickstart.html); we'd love to hear your feedback.

---

North of 500k Python developers use Hypothesis to test their code[^1], making Hypothesis the most popular property-based testing framework across any language. For good reason; property-based testing is great for specifying and testing invariants.

Today, we're excited to take this success one step farther by introducing [HypoFuzz](https://hypofuzz.com/), a fuzzing backend and dashboard for your Hypothesis tests. We think there is a wealth of untapped potential in combining property-based testing and fuzzing, and the goal of HypoFuzz is to make this combination effortless and transparent.

![HypoFuzz dashboard]({static}/images/hypofuzz_dashboard.webp)

Using HypoFuzz has two big benefits:

* **Find deep bugs** with zero extra work or annoying fuzz harnesses. HypoFuzz takes your Hypothesis tests and transparently executes them using an ensemble fuzzer. Nothing changes about how you write Hypothesis tests, except that you juice more out of them with HypoFuzz.
* **Understand your tests.** Ever written a test and been suspicious when it passes first-try? The dashboard shows input distributions and lets you inspect individual test cases. For particularly interesting tests, you can add custom events for HypoFuzz to graph.

![HypoFuzz dashboard]({static}/images/hypofuzz_observability.webp)

HypoFuzz is free for non-commercial use. For businesses, [get in touch](mailto:sales@hypofuzz.com?subject=Evaluation%20HypoFuzz%20licence) and we'll set you up with a free 6 month evaluation license. **We want to hear from you**, so we can help make HypoFuzz work for you: [get in touch](mailto:hello@hypofuzz.com?subject=HypoFuzz) or [book a chat](https://calendar.app.google/XDBzPvxbLaP2tQLE8) to tell us what you want to see in HypoFuzz, or in general fuzzing / PBT workflows!

We think we've made something pretty special here, and we're excited [for you to try it](https://hypofuzz.com/docs/quickstart.html).

[^1]: 4-5% of yearly PSF survey respondents use Hypothesis, multiplied by north of ten million Python developers.
