---
layout: post
tags: news python non-technical
date: 2016-07-09 00:00
title: Hypothesis for Python 3.4.1 Release
published: true
author: drmaciver
---

This is a bug fix release for a single bug:

*   On Windows when running two Hypothesis processes in parallel (e.g.
    using pytest-xdist) they could race with each other and one would
    raise an exception due to the non-atomic nature of file renaming on
    Windows and the fact that you can’t rename over an existing file.
    This is now fixed.

## Notes

My tendency of doing immediate patch releases for bugs is unusual but
generally seems to be appreciated. In this case this was a bug that was
blocking
[a py.test merge](https://github.com/pytest-dev/pytest/pull/1705).

I suspect this is not the last bug around atomic file creation on
Windows. Cross platform atomic file creation seems to be a harder
problem than I would have expected.
