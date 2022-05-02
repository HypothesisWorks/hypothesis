---
layout: post
tags: news python non-technical
date: 2016-07-13 00:00
title: 3.4.2 Release of Hypothesis for Python
published: true
author: drmaciver
---

This is a bug fix release, fixing a number of problems with the settings
system:

* Test functions defined using @given can now be called from other
  threads (Issue #337)
* Attempting to delete a settings property would previously have
  silently done the wrong thing. Now it raises an AttributeError.
* Creating a settings object with a custom database_file parameter
  was silently getting ignored and the default was being used instead.
  Now it’s not.

## Notes

For historic reasons, _settings.py had been excluded from the
requirement to have 100% branch coverage. Issue #337 would have been
caught by a coverage requirement: the code in question simply couldn't
have worked, but it was not covered by any tests, so it slipped through.

As part of the general principle that bugs shouldn't just be fixed
without addressing the reason why the bug slipped through in the first
place, I decided to impose the coverage requirements on _settings.py
as well, which is how the other two bugs were found. Both of these had
code that was never run during tests - in the case of the deletion bug
there was a \_\_delete\_\_ descriptor method that was never being run,
and in the case of the database\_file one there was a check later that
could never fire because the internal \_database field was always being
set in \_\_init\_\_.

I feel like this experiment thoroughly validated that 100% coverage is a
useful thing to aim for. Unfortunately it also pointed out that the
settings system is *much* more complicated than it needs to be. I'm
unsure what to do about that - some of its functionality is a bit too
baked into the public API to lightly change, and I'm don't think it's
worth breaking that just to simplify the code.
