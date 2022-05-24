---
layout: post
tags: news python non-technical
date: 2016-10-01 00:00
title: Seeking funding for deeper integration between Hypothesis and pytest
published: true
author: drmaciver
---

Probably the number one complaint I hear from Hypothesis users is that it
"doesn't work" with py.test fixtures. [This isn't true](http://hypothesis.works/articles/hypothesis-pytest-fixtures/),
but it does have one very specific limitation in how it works that annoys people:
It only runs function scoped fixtures once for the entire test, not once per
example. Because of the way people use function scoped fixtures for handling
stateful things like databases, this often causes people problems.

I've been [maintaining for a while](https://github.com/pytest-dev/pytest/issues/916) that
this is impossible to fix without some changes on the pytest end.

The good news is that this turns out not to be the case. After some conversations with
pytest developers, some examining of other pytest plugins, and a bunch of prototyping,
I'm pretty sure it's possible. It's just really annoying and a lot of work.

So that's the good news. The bad news is that this isn't going to happen without
someone funding the work.

I've now spent about a week of fairly solid work on this, and what I've got is
quite promising: The core objective of running pytest fixtures for every examples
works fairly seamlessly.

But it's now in the long tail of problems that will need to be squashed before
this counts as an actual production ready releasable piece of work. A number of
things *don't* work. For example, currently it's running some module scoped
fixtures once per example too, which it clearly shouldn't be doing. It also
currently has some pretty major performance problems that are bad enough that
I would consider them release blocking.

As a result I'd estimate there's easily another 2-3 weeks of work needed to
get this out the door.

Which brings us to the crux of the matter: 2-3 additional weeks of free work
on top of the one I've already done is 3-4 weeks more free work than I
particularly want to do on this feature, so without sponsorship it's not
getting finished.

I typically charge £400/day for work on Hypothesis (this is heavily discounted
off my normal rates), so 2-3 weeks comes to £4000 to £6000 (roughly $5000
to $8000) that has to come from somewhere.

I know there are a number of companies out there using pytest and Hypothesis
together. I know from the amount of complaining about this integration that
this is a real problem you're experiencing. So, I think this money should
come from those companies. Besides helping to support a tool you've already
got a lot of value out of, this will expand the scope of what you can easily
test with Hypothesis a lot, and will be hugely beneficial to your bug finding
efforts.

This is a model that has worked well before with the funding of the recent
statistics work by [Jean-Louis Fuchs](https://github.com/ganwell) and
[Adfinis-SyGroup](https://www.adfinis-sygroup.ch/), and I'm confident it can
work well again.

If you work at such a company and would like to talk about funding some or
part of this development, please email me at
[drmaciver@hypothesis.works](mailto:drmaciver@hypothesis.works).
