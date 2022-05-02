---
title: Products
layout: page
date: 2015-05-19 15:00
---

## Hypothesis for Python

This is our current primary focus and the only currently production ready
implementation of the Hypothesis design.

It features:

* A full implementation of [property based testing](
  {{site.url}}{% post_url  2016-05-13-what-is-property-based-testing %}) for
  Python, including [stateful testing]({{site.url}}{% post_url  2016-04-19-rule-based-stateful-testing %}).
* An extensive library of data generators and tools for writing your own.
* Compatible with py.test, unittest, nose and Django testing, and probably many
  others besides.
* Supports CPython and PyPy 3.6 and later (older versions are EoL upstream).
* Open source under the [Mozilla Public License 2.0](https://www.mozilla.org/en-US/MPL/2.0/)

To use Hypothesis for Python, simply add the *hypothesis* package to your requirements,
or *pip install hypothesis* directly.

The code is [available on GitHub](https://github.com/HypothesisWorks/hypothesis-python)
and documentation is available [on readthedocs](https://hypothesis.readthedocs.io/).

## Hypothesis for Java

Hypothesis for Java is currently a *feasibility prototype* only and is not ready
for production use. We are looking for initial customers to help fund getting it
off the ground.

As a prototype it currently features:

* Enough of the core Hypothesis model to be useful.
* Good JUnit integration.
* A small library of data generators.

The end goal is for Hypothesis for Java to have feature parity with Hypothesis
for Python, and to take advantage of the JVM's excellent concurrency support
to provide parallel testing of your code, but it's not there yet.

The current prototype is released under the AGPL3 (this is not the intended
license for the full version, which will most likely be Apache licensed) and
is [available on GitHub](https://github.com/HypothesisWorks/hypothesis-java).

Email us at [hello@hypothesis.works](mailto:hello@hypothesis.works) if you want
to know more about Hypothesis for Java or want to discuss being an early customer
of it.
