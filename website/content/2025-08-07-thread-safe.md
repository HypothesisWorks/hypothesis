---
date: 2025-08-07 00:00
title: Hypothesis is now thread-safe
author: Liam DeVoe
---

*TL;DR: as of [version 6.136.9](https://hypothesis.readthedocs.io/en/latest/changelog.html#v6-136-9), Hypothesis supports running the same test simultaneously from multiple threads.*

Hypothesis has historically had the following thread-safety policy:

* Running tests in multiple processes: fully supported.
* Running separate tests in multiple threads: not officially supported, but mostly worked.
* Running the same test in multiple threads: not supported, and didn't work.

No longer! In a series of releases spanning from [v6.135.17](https://hypothesis.readthedocs.io/en/latest/changelog.html#v6-135-17) to [v6.136.9](https://hypothesis.readthedocs.io/en/latest/changelog.html#v6-136-9), Hypothesis has gained official support for all three of these cases. You can read about the details of what we now guarantee [here](https://hypothesis.readthedocs.io/en/latest/compatibility.html#thread-safety-policy). The now-historic tracking issue is [here](https://github.com/HypothesisWorks/hypothesis/issues/4451).

## Why now?

While we of course would always have loved for Hypothesis to be thread-safe, thread-safety has historically not been a priority, because running Hypothesis tests under multiple threads is not something we see often.

That changed recently. Python—as both a language, and a community—is gearing up to [remove the global interpreter lock (GIL)](https://peps.python.org/pep-0703/), in a build called [free threading](https://docs.python.org/3/howto/free-threading-python.html). Python packages, especially those that interact with the C API, will need to test that their code still works under the free threaded build. A great way to do this is to run each test in the suite in two or more threads simultaneously.

Where does Hypothesis fit into this? When I was at [PyCon 2025](https://us.pycon.org/2025/) in May earlier this year, I talked with [Nathan Goldbaum](https://github.com/ngoldbaum) from [Quansight](https://quansight.com/), who is one of the people working on community free threading compatibility. Nathan mentioned that because Hypothesis is not thread-safe, Hypothesis tests in community packages have to be skipped when testing free threaded compatibility, which removes a substantial battery of coverage.

As a result, Quansight contracted me to work on making Hypothesis thread-safe. I enjoy contributing to Hypothesis in my free time even without a monetary incentive, so this was a pleasure to do, and Nathan and Quansight were great to work with. (Seriously: it's thanks to them funding my time that Hypothesis is now thread-safe!)


## A note on compatibility

Free threading may have been the impetus for making Hypothesis thread-safe, but the thread-safety of Hypothesis is not tied to it. Even in the unlikely event that free threading is rolled back tomorrow by the Steering Council, Hypothesis will continue to remain thread-safe.

Now, go forth and run Hypothesis in parallel!
