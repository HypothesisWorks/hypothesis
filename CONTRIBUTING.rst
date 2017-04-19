=============
Contributing
=============

First off: It's great that you want to contribute to Hypothesis! Thanks!

The process is a little involved (don't worry, I'll help you through it), so
do read this document first.

-----------------------
Copyright and Licensing
-----------------------

It's important to make sure that you own the rights to the work you are submitting.
If it is done on work time, or you have a particularly onerous contract, make sure
you've checked with your employer.

All work in Hypothesis is licensed under the terms of the
`Mozilla Public License, version 2.0 <http://mozilla.org/MPL/2.0/>`_. By
submitting a contribution you are agreeing to licence your work under those
terms.

Finally, if it is not there already, add your name (and a link to your GitHub
and email address if you want) to the list of contributors found at
the end of this document, in alphabetical order. It doesn't have to be your
"real" name (whatever that means), any sort of public identifier
is fine. In particular a GitHub account is sufficient.

-----------------------
The actual contribution
-----------------------

OK, so you want to make a contribution and have sorted out the legalese. What now?

First off: If you're planning on implementing a new feature, talk to me first! I'll probably
tell you to go for it, but I might have some feedback on aspects of it or tell you how it fits
into the broader scheme of things. Remember: A feature is for 3.x, not just for Christmas. Once
a feature is in, it can only be evolved in backwards compatible ways until I bump the "I can break
your code" number and release Hypothesis 4.0. This means I spend a lot of time thinking about
getting features right. It may sometimes also mean I reject your feature, or feel you need to
rethink it, so it's best to have that conversation early.

Once you've done that, feel free to ask me for help as you go. You're welcome to submit a work in
progress pull request early if you want feedback, just please mark it as such.

The review process will probably take some time, with me providing feedback on what I like about
your work and what I think could use improving. Particularly when adding features it's very unlikely
I'll accept a pull request as is, but that's not a sign that I don't like your code and you shouldn't
get discouraged.

Before it's merged your contribution will have to be:

1. Tested (the build will probably fail if it's not, but even if the build passes new work needs test)
2. Documented
3. Complying to the code standard (running 'make format' locally will fix most formatting errors and 'make lint'
   will tell you about the rest)
4. Otherwise passing the build

Note: If you can't figure out how to test your work, I'm happy to help. If *I* can't figure out how to
test your work, I may pass it anyway.

~~~~~~~~~
The build
~~~~~~~~~

The build is orchestrated by a giant Makefile which handles installation of the relevant pythons.
Actually running the tests is managed by `tox <https://tox.readthedocs.io/en/latest/>`_, but the Makefile
will call out to the relevant tox environments so you mostly don't have to know anything about that
unless you want to make changes to the test config. You also mostly don't need to know anything about make
except to type 'make' followed by the name of the task you want to run.

All of it will be checked on Travis so you don't *have* to run anything locally, but you might
find it useful to do so: A full travis run takes about an hour, so running a smaller set of
tests locally can be helpful.

The makefile should be "fairly" portable, but is currently only known to work on Linux or OS X. It *might* work
on a BSD or on Windows with cygwin installed, but it probably won't.

Some notable commands:

'make format' will reformat your code according to the Hypothesis coding style. You should use this before each
commit ideally, but you only really have to use it when you want your code to be ready to merge.

You can also use 'make check-format', which will run format and some linting and will then error if you have a
git diff. Note: This will error even if you started with a git diff, so if you've got any uncommitted changes
this will necessarily report an error.

'make check' will run check-format and all of the tests. Warning: This will take a *very* long time. On travis the
currently takes multiple hours of total build time (it runs in parallel on Travis so you don't have to wait
quite that long). If you've got a multi-core machine you can run 'make -j 2' (or any higher number if you want
more) to run 2 jobs in parallel, but to be honest you're probably better off letting travis run this step.

You can also run a number of finer grained make tasks:

* check-fast runs a fast but reasonably comprehensive subset of make check. It's still not *that* fast, but it
  takes a couple of minutes instead of a couple of hours.
* You can run the tests just for a single version of Python using one of check-py26, check-py27, check-py34,
  check-py35, check-pypy.
* check-coverage will run a subset of the tests on python 3.5 and then assert that this gave 100% coverage
* lint will just run some source code checks.
* check-django will just run tests for the django integration
* check-pytest will just run tests for the pytest plugin

Note: The build requires a lot of different versions of python, so rather than have you install them yourself,
the makefile will install them itself in a local directory. This means that the first time you run a task you
may have to wait a while as the build downloads and installs the right version of python for you.

----------------------------
If Pull Requests put you off
----------------------------

If you don't feel able to contribute code to Hypothesis that's *100% OK*. There
are lots of other things you can do to help too!

For example, it's super useful and highly appreciated if you do any of:

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo

Or, if you're OK with the pull request but don't feel quite ready to touch the code, you can always
help to improve the documentation. Spot a tyop? Fix it up and send me a pull request!

If you need any help with any of these, get in touch and I'll be extremely happy to provide it.

--------------------
List of Contributors
--------------------

The primary author for most of Hypothesis is David R. MacIver (me). However the following
people have also contributed work. As well as my thanks, they also have copyright over
their individual contributions.

* `Adam Johnson <https://github.com/adamchainz>`_
* `Adam Sven Johnson <https://www.github.com/pkqk>`_
* `Alex Stapleton <https://www.github.com/public>`_
* `Alex Willmer <https://github.com/moreati>`_ (`alex@moreati.org.uk <mailto:alex@moreati.org.uk>`_)
* `Charles O'Farrell <https://www.github.com/charleso>`_
* `Chris Down  <https://chrisdown.name>`_
* `Christopher Martin <https://www.github.com/chris-martin>`_ (`ch.martin@gmail.com <mailto:ch.martin@gmail.com>`_)
* `Cory Benfield <https://www.github.com/Lukasa>`_
* `Cristi Cobzarenco <https://github.com/cristicbz>`_ (`cristi@reinfer.io <mailto:cristi@reinfer.io>`_)
* `David Bonner <https://github.com/rascalking>`_ (`dbonner@gmail.com <mailto:dbonner@gmail.com>`_)
* `Derek Gustafson <https://www.github.com/degustaf>`_
* `Florian Bruhin <https://www.github.com/The-Compiler>`_
* `follower <https://www.github.com/follower>`_
* `Jeremy Thurgood <https://github.com/jerith>`_
* `JP Viljoen <https://github.com/froztbyte>`_ (`froztbyte@froztbyte.net <mailto:froztbyte@froztbyte.net>`_)
* `Jonty Wareing <https://www.github.com/Jonty>`_ (`jonty@jonty.co.uk <mailto:jonty@jonty.co.uk>`_)
* `kbara <https://www.github.com/kbara>`_
* `Lee Begg <https://www.github.com/llnz2>`_
* `marekventur <https://www.github.com/marekventur>`_
* `Marius Gedminas <https://www.github.com/mgedmin>`_ (`marius@gedmin.as <mailto:marius@gedmin.as>`_)
* `Markus Unterwaditzer <http://github.com/untitaker/>`_ (`markus@unterwaditzer.net <mailto:markus@unterwaditzer.net>`_)
* `Matt Bachmann <https://www.github.com/bachmann1234>`_ (`bachmann.matt@gmail.com <mailto:bachmann.matt@gmail.com>`_)
* `Max Nordlund <https://www.github.com/maxnordlund>`_ (`max.nordlund@gmail.com <mailto:max.nordlund@gmail.com>`_)
* `mulkieran <https://www.github.com/mulkieran>`_
* `Nicholas Chammas <https://www.github.com/nchammas>`_
* `Richard Boulton <https://www.github.com/rboulton>`_ (`richard@tartarus.org <mailto:richard@tartarus.org>`_)
* `Saul Shanabrook <https://www.github.com/saulshanabrook>`_ (`s.shanabrook@gmail.com <mailto:s.shanabrook@gmail.com>`_)
* `Tariq Khokhar <https://www.github.com/tkb>`_ (`tariq@khokhar.net <mailto:tariq@khokhar.net>`_)
* `Will Hall <https://www.github.com/wrhall>`_ (`wrsh07@gmail.com <mailto:wrsh07@gmail.com>`_)
* `Will Thompson <https://www.github.com/wjt>`_ (`will@willthompson.co.uk <mailto:will@willthompson.co.uk>`_)
* `Zac Hatfield-Dodds <https://www.github.com/Zac-HD>`_ (`zac.hatfield.dodds@gmail.com <mailto:zac.hatfield.dodds@gmail.com>`_)


-----------------
Review Guidelines
-----------------

All changes to Hypothesis go through a code review process, and must be
signed off by at least one person with write access to the repo other
than the author of the change. This document
outlines some guidelines on what to look for and what we're interested
in. It applies uniformly to maintainers and external contributors.

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

The rest of this section outlines specific things reviewers should
focus on in aid of this, broken up by sections according to their area
of applicability.

All of these conditions must be satisfied for merge. Where the reviewer
thinks this conflicts with the above higher level goals, they may make
an exception if both the author and another maintainer agree.

~~~~~~~~~~~~~~~~~
General Questions
~~~~~~~~~~~~~~~~~

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
of their nature.

1. The code should be clear in its intent and behaviour.
2. Behaviour changes should come with appropriate tests to demonstrate
   the new behaviour.
3. Hypothesis must never be *flaky*. Flakiness here is
   defined as anything where a test fails and this does not indicate
   a bug in Hypothesis or in the way the user wrote the code or the test.

~~~~~~~~~~~
API Changes
~~~~~~~~~~~

Public API changes require the most careful scrutiny of all reviews,
because they are the ones we are stuck with for the longest: Hypothesis
follows semver and additionally tries not to break API compatibility
wherever possible.

When a public API changes we should ask the following questions:

1. All public API changes must be well documented. If it's not documented,
   it doesn't count as public API!
2. Changes must be backwards compatible. Where this is not possible, they
   must first introduce a deprecation warning, then once the major version
   is bumped the deprecation warning and the functionality may be removed.
3. If an API is deprecated, the deprecation warning must make it clear
   how the user should modify their code to adapt to this change (
   possibly by referring to documentation).
4. If it is likely that we will want to make backwards compatible changes
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
