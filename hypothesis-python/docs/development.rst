======================
Hypothesis development
======================

Hypothesis development is managed by `David R. MacIver <https://www.drmaciver.com>`_
and `Zac Hatfield-Dodds <https://zhd.dev>`_, respectively the first author and lead
maintainer.

*However*, these roles don't include unpaid feature development on Hypothesis.
Our roles as leaders of the project are:

1. Helping other people do feature development on Hypothesis
2. Fixing bugs and other code health issues
3. Improving documentation
4. General release management work
5. Planning the general roadmap of the project
6. Doing sponsored development on tasks that are too large or in depth for other people to take on

So all new features must either be sponsored or implemented by someone else.
That being said, the maintenance team takes an active role in shepherding pull requests and
helping people write a new feature (see :gh-file:`CONTRIBUTING.rst` for
details and :gh-link:`these examples of how the process goes
<pulls?q=is%3Apr+is%3Amerged+mentored>`). This isn't
"patches welcome", it's "we will help you write a patch".


.. _release-policy:

Release policy
==============

Hypothesis releases follow `semantic versioning <https://semver.org/>`_.

We maintain backwards-compatibility wherever possible, and use deprecation
warnings to mark features that have been superseded by a newer alternative.
If you want to detect this, you can
:mod:`upgrade warnings to errors in the usual ways <python:warnings>`.

We use continuous deployment to ensure that you can always use our newest and
shiniest features - every change to the source tree is automatically built and
published on PyPI as soon as it's merged onto master, after code review and
passing our extensive test suite.


Project roadmap
===============

Hypothesis does not have a long-term release plan.  We respond to bug reports
as they are made; new features are released as and when someone volunteers to
write and maintain them.
