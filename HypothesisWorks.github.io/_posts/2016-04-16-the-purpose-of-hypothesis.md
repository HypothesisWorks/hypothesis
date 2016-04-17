---
layout: post
tags: writing-good-software principles non-technical
date: 2016-04-16 12:00
title: The Purpose of Hypothesis
published: true
---

What is Hypothesis for?

From the perspective of a user, the purpose of Hypothesis is to make it easier for you
to write better tests.

From my perspective as the primary author, that is of course also *a* purpose of Hypothesis.
I write a lot of code, it needs testing, and the idea of trying to do that without Hypothesis
has become nearly unthinkable.

But, on a large scale, the true purpose of Hypothesis is to drag the world kicking and screaming
into a new and terrifying age of high quality software.

<!--more-->

Software is everywhere. We have built a civilization on it, and it's only getting more prevalent
as more services move online and embedded and "internet of things" devices become cheaper and
more common.

Software is also terrible. It’s buggy, it's insecure, and it's rarely well thought out.

This combination is clearly a recipe for disaster.

The state of software testing is even worse. It’s uncontroversial at this point that you *should*
be testing your code, but it's a rare codebase whose authors could honestly claim that they feel
its testing is sufficient.

Much of the problem here is that it’s too hard to write good tests. Tests take up a vast quantity
of development time, but they mostly just laboriously encode exactly the same assumptions and
fallacies that the authors had when they wrote the code, so they miss exactly the same bugs that
you missed when they wrote the code.

Meanwhile, there are all sorts of tools for making testing better that are basically unused, or
used in only specialised contexts. The original Quickcheck is from 1999 and the majority of
developers have not even heard of it, let alone used it. There are a bunch of half-baked
implementations for most languages, but very few of them are worth using. More recently, there
are many good tools applied to specialized problems, but very little that even attempts, let
alone succeeds, to help general purpose testing.

The goal of Hypothesis is to fix this, by taking research level ideas and applying solid
engineering to them to produce testing tools that are both powerful *and* practical, and
are accessible to everyone..

Many of the ideas that Hypothesis is built on are new. Many of them are not. It doesn't matter.
The purpose of Hypothesis is not to produce research level ideas. The purpose of Hypothesis is
to produce high quality software by any means necessary. Where the ideas we need exist, we
will use them. Where they do not, we will invent them.

If people aren't using advanced testing tools, that's a bug. We should find it and fix it.

Fortunately, we have this tool called Hypothesis. It's very good at finding bugs. But this
one it can also fix.
