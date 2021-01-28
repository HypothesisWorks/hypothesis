===================================
The Hypothesis Code Review Handbook
===================================

Note: This review guide was written with the Python version in mind,
but should apply to *all* versions. If you find a place where it's a bit
too Python specific, please fix it or file an issue.

This document outlines the process for reviewing changes to Hypothesis. It's
partly descriptive, partly prescriptive, and entirely prone to change in
response to circumstance and need. We're still figuring this thing out!

-----------------
What Needs Review
-----------------

The repository includes Hypothesis implementations for multiple languages,
which have different review requirements due to different levels of project
maturity:

- all changes to hypothesis-python and the language-independent build
  infrastructure must be signed off by at least one person with write access to
  the repo other than the author of the change. (These requirements will apply
  to any Hypothesis implementations with a 1.0 release.)
- changes by `DRMacIver <https://github.com/DRMacIver>`_ to hypothesis-ruby do
  not require review, but will be posted as pull requests, often for long
  enough that if someone wants to review and ask questions, they can.

----------------
How Review Works
----------------

Once the build is green and a reviewer has approved the change, anyone on the
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


~~~~~~~~~~~~~
Orthogonality
~~~~~~~~~~~~~

For all minor or patch releases, we enforce a hard and fast rule that they
contain no more than one user-visible change. Major releases are allowed
to bundle multiple changes together, but these should be structured as
smaller pull requests into some tracking branch.

We are currently very bad at this, so reviewers should feel empowered
to be extra strict and provide a lot of push back on this.

What counts as a user visible change is somewhat up to individual
judgement, but you should err in the direction of assuming that
if it might count then it does count.

A good rule of thumb is that if the ``RELEASE.rst`` uses the words "additionally"
or needs bullet points to be clear, it is likely too large.

Ideally changes that are not user visible should also be self-contained
into their own releases, but a certain amount of leniency is permitted -
it's certainly OK to do a moderate amount of refactoring while you're
in the area, and if a pull request involves no release at all then the same
level of orthogonality is not required (but is still desirable).

~~~~~~~~~~~~~~~~~~~~~~
Clarity of Description
~~~~~~~~~~~~~~~~~~~~~~

The ``RELEASE.rst`` should contain a description of the change that
makes clear:

1. The motivation for the change
2. The likely consequences of the change

This doesn't have to be an essay. If you're following the orthogonality
requirements a paragraph or two is likely sufficient.

Any additional information that is useful to reviewers should be provided
in the pull request comment. This can include e.g. background, why the
particular approach was taken, references to internals that are unlikely
to be of interest to users.

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
4. The changelog (in ``RELEASE.rst``) should bump the minor or patch version
   (see guides/documentation.rst for details), accurately describe the
   changes, and shouldn't refer to internal-only APIs.  For complicated
   markup, consider building the docs and manually checking the changelog
   for formatting errors that didn't result in a compilation error.

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
   If the required code change could be automated, the deprecation should have either
   `a codemod to fix it <https://github.com/HypothesisWorks/hypothesis/issues/2705>`__
   or a tracking issue to write one (see "asking for more work" below).
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
8. `DRMacIver <https://github.com/DRMacIver>`_ or
   `Zac-HD <https://github.com/Zac-HD>`_ must approve the changes
   though other maintainers are welcome and likely to chip in to review as
   well.
9. We have a separate guide for `house API style <api-style.rst>`_ which should
   be followed. Note that currently this only covers the API style for the Python
   version. We are still figuring out the API style for the Ruby version.

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

Note: This section currently only applies to the Python version.

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

When deprecating a setting for later removal, we prefer to change the default
value of the setting to a private singleton (``not_set``), and implement the
future behaviour immediately.  Passing any other value triggers a deprecation
warning, but is otherwise a no-op (i.e. we still use the future behaviour).

For settings where this would be especially disruptive, we have also prefixed
that deprecation process with a process where we emit a warning, add a special
value that can be passed to opt-in to the future behaviour, and then in the
following major release we deprecate *that*, make it an no-op, and make it an
error to pass any other value.

~~~~~~~~~~~~~~
Engine Changes
~~~~~~~~~~~~~~

Engine changes are anything that change a "fundamental" of how Hypothesis
works. A good rule of thumb is that an engine change is anything that touches
a file in ``hypothesis.internal.conjecture`` (Python version).

All such changes should:

1. Be approved (or authored) by DRMacIver or Zac-HD.
2. Be approved (or authored) by someone who *isn't* DRMacIver (a major problem
   with this section of the code is that there is too much that only DRMacIver
   understands properly and we want to fix this).
3. If appropriate, come with a test in test_discovery_ability.py showing new
   examples that were previously hard to discover.
4. If appropriate, come with a test in test_shrink_quality.py showing how they
   improve the shrinker.

Note that the same rules will apply to the Ruby and Rust packages from version
1.0, but are more relaxed in practice while we are catching up with features
that are already well proven in Python.

~~~~~~~~~~~~~~~~~~~~~~
Non-Blocking Questions
~~~~~~~~~~~~~~~~~~~~~~

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

~~~~~~~~~~~~~~~~~~~~
Asking for more work
~~~~~~~~~~~~~~~~~~~~

Reviewers should in general not request changes that expand the scope of
a pull request beyond its original intended goal. The primary design
philosophy of our work-flow is that making correct changes should be cheap,
and scope creep on pull requests works against that - If you can't touch
something without having to touch a number of related areas as well,
changing things becomes expensive again.

This of course doesn't cover things where additional work is required to
ensure the change is actually correct - for example, if you change public
functionality you certainly need to update its documentation. That isn't
scope creep, that's just the normal scope.

If a pull request suggests additional work then between the reviewer and the
author people should ensure that there are relevant tracking issues for that
work (as per question 3 in "Non-Blocking Questions" above), but there is no
obligation for either of them to actually do any of the work on those issues.
By default it is the reviewer who should open these issues, but the author
is welcome to as well.

That being said, it's legitimate to expand the scope of a pull request in
some cases. For example:

* If not doing so is likely to cause problems later. For example, because
  of backwards compatibility requirements it might make sense to ask for some
  additional functionality that is likely to be added later so that the arguments
  to a function are in a more sensible order.
* Cases where the added functionality feels extremely incomplete in some
  way without an additional change. The litmus test here should be "this will
  almost never be useful because...". This is still fairly subjective, but at
  least one good use case where the change is a clear improvement over the status
  quo is enough to indicate that this doesn't apply.

If it's unclear, the reviewer should feel free to suggest additional work
(but if the author is someone new, please make sure that it's clear that this
is a suggestion and not a requirement!), but the author of the pull request should
feel equally free to decline the suggestion.
