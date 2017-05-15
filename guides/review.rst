===================================
The Hypothesis Code Review Handbook
===================================

Hypothesis has a process of reviewing every change, internal or external.
This is a document outlining that process. It's partly descriptive, partly
prescriptive, and entirely prone to change in response to circumstance
and need. We're still figuring this thing out!

----------------
How Review Works
----------------

All changes to Hypothesis must be signed off by at least one person with
write access to the repo other than the author of the change. Once the
build is green and a reviewer has approved the change, anyone on the
maintainer team may merge the request.

More than one maintainer *may* review a change if they wish to, but it's
not required. Any maintainer may block a pull request by requesting changes.

Consensus on a review is best but not required. If some reviewers have
approved a pull request and some have requested changes, ideally you
would try to address all of the changes, but it is OK to dismiss dissenting
reviews if you feel it appropriate.

We've not tested the case of differing opinions much in practice yet, so
we may grow firmer guidelines on what to do there over time.

------------
Review Goals
------------

At a high level, the two things we're looking for in review are answers
to the following questions:

1. Is this change going to make users' lives worse?
2. Is this change going to make the maintainers' lives worse?

Code review is a collaborative process between the author and the
reviewer to try to ensure that the answer to both of those questions
is no.

Ideally of course the change should also make one or both of the users'
and our lives *better*, but it's OK for changes to be mostly neutral.
The author should be presumed to have a good reason for submitting the
change in the first place, so neutral is good enough!

--------------
Social Factors
--------------

* Always thank external contributors. Thank maintainers too, ideally!
* Remember that the `Code of Conduct <https://hypothesis.readthedocs.io/en/latest/community.html#code-of-conduct>`_
  applies to pull requests and issues too. Feel free to throw your weight
  around to enforce this if necessary.
* Anyone, maintainer or not, is welcome to do a code review. Only official
  maintainers have the ability to actually approve and merge a pull
  request, but outside review is also welcome.

------------
Requirements
------------

The rest of this document outlines specific things reviewers should
focus on in aid of this, broken up by sections according to their area
of applicability.

All of these conditions must be satisfied for merge. Where the reviewer
thinks this conflicts with the above higher level goals, they may make
an exception if both the author and another maintainer agree.


~~~~~~~~~~~~~~~~~~~~
General Requirements
~~~~~~~~~~~~~~~~~~~~

The following are required for almost every change:

1. Changes must be of reasonable size. If a change could logically
   be broken up into several smaller changes that could be reviewed
   separately on their own merits, it should be.
2. The motivation for each change should be clearly explained (this
   doesn't have to be an essay, especially for small changes, but
   at least a sentence of explanation is usually required).
3. The likely consequences of a change should be outlined (again,
   this doesn't have an essay, and it may be sufficiently
   self-explanatory that the motivation section is sufficient).

~~~~~~~~~~~~~~~~~~~~~
Functionality Changes
~~~~~~~~~~~~~~~~~~~~~

This section applies to any changes in Hypothesis's behaviour, regardless
of their nature. A good rule of thumb is that if it touches a file in
src then it counts.

1. The code should be clear in its intent and behaviour.
2. Behaviour changes should come with appropriate tests to demonstrate
   the new behaviour.
3. Hypothesis must never be *flaky*. Flakiness here is
   defined as anything where a test fails and this does not indicate
   a bug in Hypothesis or in the way the user wrote the code or the test.
4. The version number must be kept up to date, following
   `Semantic Versioning <http://semver.org/>`_ conventions: The third (patch)
   number increases for things that don't change public facing functionality,
   the second (minor) for things that do but are backwards compatible, and
   the first (major) changes for things that aren't backwards compatible.
   See the section on API changes for the latter two.
5. The changelog should be kept up to date, clearly describing the change
   and including the current date (remember: This will be released as soon
   as it's merged).

~~~~~~~~~~~
API Changes
~~~~~~~~~~~

Public API changes require the most careful scrutiny of all reviews,
because they are the ones we are stuck with for the longest: Hypothesis
follows semantic versioning, and we don't release new major versions
very often.

Public API changes must satisfy the following:

1. All public API changes must be well documented. If it's not documented,
   it doesn't count as public API!
2. Changes must be backwards compatible. Where this is not possible, they
   must first introduce a deprecation warning, then once the major version
   is bumped the deprecation warning and the functionality may be removed.
3. If an API is deprecated, the deprecation warning must make it clear
   how the user should modify their code to adapt to this change (
   possibly by referring to documentation).
4. If it is likely that we will want to make backwards incompatible changes
   to an API later, to whatever extent possible these should be made immediately
   when it is introduced instead.
5. APIs should give clear and helpful error messages in response to invalid inputs.
   In particular error messages should always display
   the value that triggered the error, and ideally be specific about the
   relevant feature of it that caused this failure (e.g. the type).
6. Incorrect usage should never "fail silently" - when a user accidentally
   misuses an API this should result in an explicit error.
7. Functionality should be limited to that which is easy to support in the
   long-term. In particular functionality which is very tied to the
   current Hypothesis internals should be avoided.
8. `DRMacIver <https://github.com/DRMacIver>`_ must approve the changes
   though other maintainers are welcome and likely to chip in to review as
   well).

~~~~~~~~~
Bug Fixes
~~~~~~~~~

1. All bug fixes must come with a test that demonstrates the bug on master and
   which is fixed in this branch. An exception *may* be made here if the submitter
   can convincingly argue that testing this would be prohibitively difficult.
2. Where possible, a fix that makes it impossible for similar bugs to occur is
   better.
3. Where possible, a test that will catch both this bug and a more general class
   of bug that contains it is better.

~~~~~~~~~~~~~~~~
Settings Changes
~~~~~~~~~~~~~~~~

It is tempting to use the Hypothesis settings object as a dumping ground for
anything and everything that you can think of to control Hypothesis. This
rapidly gets confusing for users and should be carefully avoided.

New settings should:

1. Be something that the user can meaningfully have an opinion on. Many of the
   settings that have been added to Hypothesis are just cases where Hypothesis
   is abdicating responsibility to do the right thing to the user.
2. Make sense without reference to Hypothesis internals.
3. Correspond to behaviour which can meaningfully differ between tests - either
   between two different tests or between two different runs of the same test
   (e.g. one use case is the profile system, where you might want to run Hypothesis
   differently in CI and development). If you would never expect a test suite to
   have more than one value for a setting across any of its runs, it should be
   some sort of global configuration, not a setting.

Removing settings is not something we have done so far, so the exact process
is still up in the air, but it should involve a careful deprecation path where
the default behaviour does not change without first introducing warnings.

~~~~~~~~~~~~~~
Engine Changes
~~~~~~~~~~~~~~

Engine changes are anything that change a "fundamental" of how Hypothesis
works. A good rule of thumb is that an engine change is anything that touches
a file in hypothesis.internal.conjecture.

All such changes should:

1. Be approved (or authored) by DRMacIver.
2. Be approved (or authored) by someone who *isn't* DRMacIver (a major problem
   with this section of the code is that there is too much that only DRMacIver
   understands properly and we want to fix this).
3. If appropriate, come with a test in test_discovery_ability.py showing new
   examples that were previously hard to discover.
4. If appropriate, come with a test in test_shrink_quality.py showing how they
   improve the shrinker.

~~~~~~~~~~~~~~~~~~~~~~~
Non-Blocking Questions
~~~~~~~~~~~~~~~~~~~~~~~

These questions should *not* block merge, but may result in additional
issues or changes being opened, either by the original author or by the
reviewer.

1. Is this change well covered by the review items and is there
   anything that could usefully be added to the guidelines to improve
   that?
2. Were any of the review items confusing or annoying when reviewing this
   change? Could they be improved?
3. Are there any more general changes suggested by this, and do they have
   appropriate issues and/or pull requests associated with them?
