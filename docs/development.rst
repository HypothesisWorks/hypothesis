==============================
Ongoing Hypothesis Development
==============================

Hypothesis development is managed by me, `David R. MacIver <http://www.drmaciver.com>`_.
I am the primary author of Hypothesis.

*However*, I no longer do unpaid feature development on Hypothesis. My roles as leader of the project are:

1. Helping other people do feature development on Hypothesis
2. Fixing bugs and other code health issues
3. Improving documentation
4. General release management work
5. Planning the general roadmap of the project
6. Doing sponsored development on tasks that are too large or in depth for other people to take on

So all new features must either be sponsored or implemented by someone else.
That being said, the maintenance team takes an active role in shepherding pull requests and
helping people write a new feature (see :gh-file:`CONTRIBUTING.rst` for
details and :pull:`154` for an example of how the process goes). This isn't
"patches welcome", it's "we will help you write a patch".


.. _release-policy:

Release Policy
==============

Hypothesis releases follow `semantic versioning <http://semver.org/>`_.

We maintain backwards-compatibility wherever possible, and use deprecation
warnings to mark features that have been superseded by a newer alternative.
If you want to detect this, the :py:meth:`strict setting <hypothesis.settings.strict>`
upgrades all Hypothesis warnings to errors.

We use continuous deployment to ensure that you can always use our newest and
shiniest features - every change to the source tree is automatically built and
published on PyPI as soon as it's merged onto master, after code review and
passing our extensive test suite.


Project Roadmap
===============

Hypothesis does not have a long-term release plan.  However some visibility
into our plans for future :doc:`compatibility <supported>` may be useful:

- We value compatibility, and maintain it as far as practical.  This generally
  excludes things which are end-of-life upstream, or have an unstable API.
- We would like to drop Python 2 support when it it reaches end of life in
  2020.  Ongoing support is likely to depend on commercial funding.
- We intend to support PyPy3 as soon as it supports a recent enough version of
  Python 3.  See :issue:`602`.
