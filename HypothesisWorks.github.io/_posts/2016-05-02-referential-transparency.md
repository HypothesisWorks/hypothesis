---
layout: post
tags: non-technical
date: 2016-05-02 08:00
title: You Don't Need Referential Transparency
published: true
author: drmaciver
---

It's a common belief that in order for property based testing to be useful, your code must be [referentially transparent](https://en.wikipedia.org/wiki/Referential_transparency). That is, it must be a pure function with no side effects that just takes input data and produces output data and is solely defined by what input data produces what output data.

This is, bluntly, complete and utter nonsense with no basis in reality.

<!--more-->


The idea comes from the fact that it was true of very early versions of [the original Haskell QuickCheck](https://hackage.haskell.org/package/QuickCheck) - it was designed to look more like formal methods than unit testing, and it was designed for a language where referential transparency was the norm.

But that was the *original* version of Haskell QuickCheck. It's not even true for the latest version of it, let alone for ports to other languages! The Haskell version has full support for testing properties in IO (if you don't know Haskell, this means "tests which may have side effects"). It works really well. Hypothesis doesn't even consider this a question - testing code with side effects works the same way as testing code without side effects.

The *only* requirement that property based testing has on the side effects your tests may perform is that if your test has *global* side effects then it must be able to roll them back at the end.

If that sounds familiar, it's because it's *exactly the same requirement every other test has*. Tests that have global side effects are not repeatable and may interfere with other tests, so they must keep their side effects to themselves by rolling them back at the end of the test.

Property based testing is just normal testing, run multiple times, with a source of data to fill in some of the blanks. There is no special requirement on it beyond that, and the myth that there is causes great harm and keeps many people from adopting more powerful testing tools.
