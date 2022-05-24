---
layout: post
tags: technical details python
date: 2017-09-28 11:00
title: The Threshold Problem
published: true
author: drmaciver
---

In [my last post]({{site.url}}{% post_url 2017-09-14-multi-bug-discovery %}) I mentioned
the problem of bug slippage: When you start with one bug, reduce the test case, and end
up with another bug.

I've run into another related problem twice now, and it's not one I've seen talked about
previously.

The problem is this: Sometimes shrinking makes a bug seem much less interesting than it
actually is.

<!--more-->

I first noticed this problem when [Ned Batchelder](https://nedbatchelder.com/) asked me
about some confusing behaviour he was seeing: He was testing some floating point code and
had an assertion that the error was not greater than some threshold. Let's say 0.5 (I could
dig up the IRC logs, but the exact number doesn't matter).

Hypothesis said "Ah ha! Here is an example where the error is 0.500001. A bug!".

Ned sighed and thought "Oh great, floating point precision issues", but on further
investigation it turned out that that wasn't it at all. The error could be arbitrarily large,
it's just that Hypothesis reliably gave an example where it was almost as small as it could
possibly be and still fail.

This wasn't a bug, either. This is how Hypothesis, QuickCheck, and all of the other tools
in this family are designed to work.

The problem is that test case reduction is designed to produce the simplest example
possible to demonstrate the bug. If the bug can be expressed as happening when some
score exceeds some threshold, and the score is one that tends to increase with example
size, then the failing example that a property-based testing library gives you will tend
to be one where the score is barely above that threshold, making the problem look much
less bad than it actually is.

This isn't even a bug in Hypothesis - QuickCheck or any other property-based testing would
do the same. It's literally working as intended.

Arguably it's not even really a problem: Hypothesis has demonstrated the bug, and it's
done so with a simple example which should thus be easy to understand.

But I can't help but feel that we could do better. It definitely produces misleading
examples even if they technically demonstrate the right problem, and misleading examples
are a great way to waste the user's time.

I also ran into this problem again recently, where it was more of a problem because it
was resulting in flaky tests.

I recently introduced [a deadline feature](https://hypothesis.readthedocs.io/en/latest/settings.html?highlight=deadline#hypothesis.settings.deadline)
as part of the work on Hypothesis performance legibility that [Smarkets](https://smarkets.com/)
are funding. This causes slow examples to be treated as failures: If an example passes
but took longer than your deadline to run, it raises `DeadlineExceeded`. This is treated
as a normal error and Hypothesis shrinks it like anything else (including allowing it to
participate in the multi-shrinking process).

The problem is that it's exactly this sort of threshold problem: You literally have a
score (the run time) and a threshold (the deadline) such that when the score exceeds
the threshold the test fails. Large examples are certainly likely to be slower, so you
will consistently get examples which are right on the boundary of being too slow.

Which is fine, except that  Hypothesis relies on repeatability to display test errors -
once it has a minimized example, it replays the test so it can show you the example,
print the exception, etc. And test run times are not actually repeatable - a test that
takes 201ms on first running might take 199ms on the next run. This then results in
Hypothesis thinking the test is flaky - it previously raised `DeadlineExceeded`, and now it
doesn't. This lead to [Issue 892](http://github.com/HypothesisWorks/hypothesis-python/issues/892),
where Florian Bruhin ran into precisely this problem when testing [Qutebrowser](https://www.qutebrowser.org/).

The [solution I've ended up opting for there](https://github.com/HypothesisWorks/hypothesis-python/pull/899)
is to temporarily raise the deadline during shrinking
to something halfway between the actual deadline and the largest runtime we've seen. This
ensures that we shrink to a larger threshold than the deadline, and then when we replay
we should comfortably exceed the real deadline unless the test performance actually *is*
really flaky (in which case I've also improved the error message).

This solution is currently very specific to the problem of the deadlines, and that's
fine - there's no need to rush to a fully general solution, and deadlines have slightly
different constraints than other variants of this due to the unreliability of timing -
but it is something I'd like to see solved more generally.

One thing I have thought about for a while is adding some notion of scoring to
Hypothesis - e.g. letting people record some score that recorded your progress
in testing (testing games where the score could be e.g. the level you've reached, or
your literal score in the game, was one use case I had in mind). This would seem to be
another good example for that - if you could make your score available to Hypothesis
in some way (or if Hypothesis could figure it out automatically!), then a similar
solution to the above could be used: If Hypothesis notices that the score of the
shrunk example is drastically different from the score of the starting example, it
could try rerunning the shrinking process with the additional constraint that the
score should stay closer to that of the original example, and display the newly shrunk
example with the larger (or smaller) score alongside it. This would work as part
of the new multiple failures reporting, so you would see both examples side by side.

This needs more thought before I jump in and implement something, but I think this is
an important problem to solve to improve the usability of Hypothesis in particular and
property-based testing in general. Shrinking is a great start to making the problems
testing exposes legible to users, but it's only a start, and we need to do more to
try to improve developers' productivity when debugging the problems we show them.
