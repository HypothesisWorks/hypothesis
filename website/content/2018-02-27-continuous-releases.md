---
tags: development-process
date: 2018-02-27 07:00
title: The Hypothesis continuous release process
author: alexwlchan
---

If you watch [the Hypothesis changelog][changelog], you'll notice the rate of releases sped up dramatically in 2017.
We released over a hundred different versions, sometimes multiple times a day.

This is all thanks to our continuous release process.
We've completely automated the process of releasing, so every pull request that changes code gets a new release, without any human input.
In this post, I'll explain how our continuous releases work, and why we find it so useful.

[changelog]: https://hypothesis.readthedocs.io/en/latest/changelog.html

<!--more-->

## How it works

In the past, Hypothesis was released manually.
Somebody had to write a changelog, tag a new release on GitHub, and run some manual pip commands to publish a new version to PyPI -- and only David had the credentials for the latter.

This meant that releases were infrequent, and features spent a long time in master before they were available to `pip install`.
The pace of development picked up in 2017 -- partly as new maintainers arrived, and partly groundwork for [David's upcoming (now started) PhD][phd] -- and we wanted to be able to release more frequently.
We decided to automate the entire release process.

Now, when you create a pull request that changes the Hypothesis code -- anything that gets installed by pip -- you have to include a `RELEASE.rst` file which describes your change.
Here's an example from [a recent pull request][recent]:

    RELEASE_TYPE: patch

    This release changes the way in which Hypothesis tries to shrink the size of
    examples. It probably won't have much impact, but might make shrinking faster
    in some cases. It is unlikely but not impossible that it will change the
    resulting examples.

The first line says whether this is a major, minor, or patch release (using [semantic versioning][semver]).
The rest is a description of the changes in your patch.

We have a test in CI that checks for this file -- any change to the core code needs a release file, even [fixing a typo][typo].
If you need a release file but haven't written one, the tests fail and your pull request won't be merged.

Sometimes we write a release file even if there aren't changes to the core code, but we think it's worth a release anyway.
For example, changes to the installation code in `setup.py`, or larger changes to our test code for the benefit of downstream packagers.

Once you've written a release file and the pull request is merged into master, and after all the other tests have passed, our CI uses this file to create a new release.

First, it works out the new version number, and updates it in [version.py][version.py].
Then it copies the release description into the changelog, including the new version number and the current date.
For example:

    --------------------
    3.44.25 - 2018-02-05
    --------------------

    This release changes the way in which Hypothesis tries to shrink the size of
    examples. It probably won't have much impact, but might make shrinking faster
    in some cases. It is unlikely but not impossible that it will change the
    resulting examples.

These two changes are saved as a new commit, and that commit gets tagged as the new release.
The tag and the commit are pushed to GitHub, and then CI builds a new package and publishes it to PyPI.

So with no very little extra work, every code change triggers a new release, and it's usually available within half an hour of merging the pull request.

This exact system might not scale to larger teams.
In particular, you can't merge new features until the code in master has been released -- you get conflicts around `RELEASE.rst` -- so you can only merge one pull request at a time.
And in Hypothesis, we never backport bugfixes to old major or minor releases -- you'd need some changes to support that.

But Hypothesis only has one full-time contributor, and everybody else works on it in their free time, we don't create patches fast enough for this to be a problem.
For us, it works exceptionally well.

[phd]: http://www.drmaciver.com/2017/04/life-changes-announcement-academia-edition/
[recent]: https://github.com/HypothesisWorks/hypothesis-python/pull/1101
[semver]: https://semver.org/
[typo]: https://github.com/HypothesisWorks/hypothesis-python/pull/1069
[version.py]: https://github.com/HypothesisWorks/hypothesis-python/blob/master/src/hypothesis/version.py

## Why bother?

Moving to continuous releases has been amazing.

The big benefit is that nobody has to do manual releases any more.
Before we had this system, changelogs had to be assembled and written by hand, which meant reading the commit log since the last release.
This is both boring and prone to error -- in the past, a release might contain multiple changes, and it was easy to overlook or forget something in the changelog.
No more!

Another benefit is that our releases happen much more quickly.
Every patch is available as soon as our tests confirm it's okay, not when somebody remembers to do a release.
If something's been merged, it's either available for download, or it will be very shortly.

Releasing more often means each individual release is much smaller, which makes it much easier to find the source of bugs or regressions.
If somebody finds a bug, we can trace it to a specific release (and corresponding pull request), and there's a relatively small amount of code to inspect.

Automation also makes our release process more reliable.
Manual steps have scope for error, and we've had a few dodgy releases in the past.
This process has cut over 100 releases near flawlessly.

Finally, every contributor gets to make a release.
If you submit a patch that gets accepted, your change is available immediately, and it's entirely your work.
This may less of tangible benefit, but it gives off nice fuzzy feelings, especially if it's your first patch.
(Speaking of which, we're always looking [for new contributors][contributors]!)

[contributors]: https://github.com/HypothesisWorks/hypothesis-python/blob/master/CONTRIBUTING.rst

## I'm ruined for everything else

I've become used to code being available almost immediately after it's merged into master -- which isn't true for the vast majority of projects.
When I go to a repo with a bug report, see that a bugfix was merged two weeks ago, but there's yet to be a new release, it's hard not to feel a little impatient.

I've started using this in my other repos -- both these scripts exactly, and derivatives of the same idea.

If you'd like to try this yourself (and I'd really encourage you to do so!), all the scripts for this process are under the same MPL license as Hypothesis itself.
Look in the [scripts directory][scripts] of the main repo.
In particular, `check-release-file.py` looks for a release note on pull requests, and `deploy.py` is what actually cuts the release.
The code will probably need tweaking for your repo (it's closely based on the Hypothesis repo), but hopefully it provides a useful starting point.

[scripts]: https://github.com/HypothesisWorks/hypothesis-python/tree/master/scripts
