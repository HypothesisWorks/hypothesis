---
layout: post
tags: news python non-technical
date: 2016-09-23 00:00
title: 3.5.0 and 3.5.1 Releases of Hypothesis for Python
published: true
author: drmaciver
---

This is a combined release announcement for two releases. 3.5.0
was released yesterday, and 3.5.1 has been released today after
some early bug reports in 3.5.0

## Changes

### 3.5.0 - 2016-09-22

This is a feature release.

* fractions() and decimals() strategies now support min_value and max_value
  parameters. Thanks go to Anne Mulhern for the development of this feature.
* The Hypothesis pytest plugin now supports a --hypothesis-show-statistics parameter
  that gives detailed statistics about the tests that were run. Huge thanks to
  Jean-Louis Fuchs and Adfinis-SyGroup for funding the development of this feature.
* There is a new event() function that can be used to add custom statistics.

Additionally there have been some minor bug fixes:

* In some cases Hypothesis should produce fewer duplicate examples (this will mostly
  only affect cases with a single parameter).
* py.test command line parameters are now under an option group for Hypothesis (thanks
  to David Keijser for fixing this)
* Hypothesis would previously error if you used function annotations on your tests under
  Python 3.4.
* The repr of many strategies using lambdas has been improved to include the lambda body
  (this was previously supported in many but not all cases).


### 3.5.1 - 2016-09-23

This is a bug fix release.

* Hypothesis now runs cleanly in -B and -BB modes, avoiding mixing bytes and unicode.
* unittest.TestCase tests would not have shown up in the new statistics mode. Now they
  do.
* Similarly, stateful tests would not have shown up in statistics and now they do.
* Statistics now print with pytest node IDs (the names you'd get in pytest verbose mode).


## Notes

Aside from the above changes, there are a couple big things behind the scenes of this
release that make it a big deal.

The first is that the flagship chunk of work, statistics, is a long-standing want to
have that has never quite been prioritised. By funding it, Jean-Louis and Adfinis-SyGroup
successfully bumped it up to the top of the priority list, making it the first funded
feature in Hypothesis for Python!

Another less significant but still important is that this release marks the first real
break with an unofficial Hypothesis for Python policy of not having any dependencies
other than the standard library and backports. This release adds a dependency on the
uncompyle6 package. This may seem like an odd choice, but it was invaluable for fixing
the repr behaviour, which in turn was really needed for providing good statistics
for filter and recursive strategies.
