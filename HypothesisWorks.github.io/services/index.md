---
title: Services and Support
layout: page
date: 2015-04-15 12:00
---

We are available to contract for a number of Hypothesis related services.

## Ports of Hypothesis to new languages

Hypothesis is designed to be easy to port to new languages, but we will rarely start on new ports
unless someone pays for the development. So if there's a language you want use Hypothesis in and you
currently can't, hire us to fix that!

As well as making Hypothesis available in a new language, we usually learn new things about the design
space when doing this which tends to produce improvements that get rolled back into other languages and
makes the next port that much easier.

We currently have [a prototype Java port](https://github.com/HypothesisWorks/hypothesis-java) and are actively
considering a port to C (which would in turn simplify the port to many other languages), but most
languages should be feasible so if you'd like a port to a different one, just ask us.

This one comes with the added bonus that it will make you very popular! We get a lot of questions about
Hypothesis ports from people who can't fund them, and anyone who funds the development of a version of
Hypothesis will get mentioned prominently in the README and documentation.

## Improve Hypothesis performance for your use case

Hypothesis performance is currently pretty good, and for most usage the bottleneck is your test code
rather than Hypothesis, but there are pathological cases where it tends to slow down. This is particularly
true if you are generating very complex data.

If you find yourself in this situation, we can help! We'll first try to help you analyze exactly *why*
your tests are slow and see if we can help you modify them to be faster. If the problem does turn out
to be something we should fix on the Hypothesis end, we can do that too.

If you're really pushing Hypothesis performance hard you may wish to consider hiring us to complete the
C port and then rebuild the version for Python (or your language of choice) on top of it.

## Paid development on Hypothesis features

As well as performance improvements, we're available for hire for any other specific development on
Hypothesis.

There are a large number of directions that Hypothesis can go in and only so much time in the day. If there's
a particular feature you need us to bump something up our priority list, you can hire us to implemement it.

## Custom testing projects

Although we think anyone can use Hypothesis (even *without* the benefit of [our training](/training/)), sometimes
you really just want an expert to do the work, either to help you get started or to give you confidence in the
results. If you have a particular piece of software that you really need to be well tested,
you can hire us to do that for you.

## Support contracts

We can provide support contracts guaranteeing priority to your bug reports and answering your questions when
you get stuck. Availability of these is somewhat limited due to capacity constraints, but we are still able
to take on new customers.

# Get in touch!

If any of the above sound just like what you need, or if there's another Hypothesis related project that doesn't
quite fit, drop us a line at [hello@hypothesis.works](mailto:hello@hypothesis.works) and lets talk
details!
