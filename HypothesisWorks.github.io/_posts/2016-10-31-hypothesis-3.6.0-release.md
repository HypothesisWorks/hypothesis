---
layout: post
tags: news python non-technical
date: 2016-10-31 00:00
title: 3.6.0 Release of Hypothesis for Python
published: true
author: drmaciver
---

This is a release announcement for the 3.6.0 release of Hypothesis for
Python. It's a bit of an emergency release.

Hypothesis 3.5.0 inadvertently added a dependency on GPLed code (see below
for how this happened) which this release removes. This means that if you
are running Hypothesis 3.5.x then there is a good chance you are in violation
of the GPL and you should update immediately.

Apologies for any inconvenience this may have caused.

<!--more-->

### From the Changelog

This release reverts Hypothesis to its old pretty printing of lambda functions
based on attempting to extract the source code rather than decompile the bytecode.
This is unfortunately slightly inferior in some cases and may result in you
occasionally seeing things like lambda x: <unknown> in statistics reports and
strategy reprs.

This removes the dependencies on uncompyle6, xdis and spark-parser.

The reason for this is that the new functionality was based on uncompyle6, which
turns out to introduce a hidden GPLed dependency - it in turn depended on xdis,
and although the library was licensed under the MIT license, it contained some
GPL licensed source code and thus should have been released under the GPL.

My interpretation is that Hypothesis itself was never in violation of the GPL
(because the license it is under, the Mozilla Public License v2, is fully
compatible with being included in a GPL licensed work), but I have not consulted
a lawyer on the subject. Regardless of the answer to this question, adding a
GPLed dependency will likely cause a lot of users of Hypothesis to inadvertently
be in violation of the GPL.

As a result, if you are running Hypothesis 3.5.x you really should upgrade to
this release immediately.

### Notes

This Halloween release brought to you by the specter of inadvertent GPL
violations (but sadly this is entirely real and neither trick nor treat).

This dependency also caused a number of other problems, so in many ways its
not entirely a bad thing that it's gone, but it's still sad to remove
functionality. At some point in the future I will try to restore the
lost functionality, but doing it without access to uncompyle6 will be a
moderate amount of work, so it's not going to be high priority in the
near future.
