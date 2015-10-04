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

Finally, if it is not there already, add your name (and a link to your github
and email address if you want) to the list of contributors found at
the end of this document, in alphabetical order. It doesn't have to be your
"real" name (whatever that means), any sort of public identifier
is fine. In particular a Github account is sufficient.

-----------------------
The actual contribution
-----------------------

OK, so you want to make a contribution and have sorted out the legalese. What now?

First off: If you're planning on implementing a new feature, talk to me first! I'll probably
tell you to go for it, but I might have some feedback on aspects of it or tell you how it fits
into the broader scheme of things. Remember: A feature is for 1.x, not just for Christmas. Once
a feature is in, it can only be evolved in backwards compatible ways until I bump the "I can break
your code" number and release Hypothesis 2.0. This means I spend a lot of time thinking about
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
3. Complying to the code standard (running 'tox -e lint' locally will fix most formatting errors)
4. Otherwise passing the build

Note: If you can't figure out how to test your work, I'm happy to help. If *I* can't figure out how to
test your work, I may pass it anyway.

~~~~~~~~~
The build
~~~~~~~~~

The build is mostly based on `tox <https://tox.readthedocs.org/en/latest/>`_, so if you've got
the relevant pythons installed (I use `pyenv <https://github.com/yyuu/pyenv>`_ to manage installs)
you can run the tests against them.

All of it will be checked on Travis so you don't *have* to run anything locally, but you might
find it useful to do so: A full travis run takes about an hour, so running a smaller set of
tests locally can be helpful.

You can either run a full tox task as 'tox -e environmentname' or you can just run of some of
the tests using py.test (some of the files will run under nose, but most are very much written
with the assumption they're running on py.test).

Some notable commands:

'tox -e lint' will run some reformatting operations and a linter then will fail the build if there
is a git diff. A common pattern I use is to commit, then lint, then amend the commit before pushing.

'tox -e coverage' will run a fast subset of the test suite under Python 3.4 and assert that it covered
100% of the branches (not counting a few files or anything with a no cover annotation on it).

'tox -e py27' will run all tests for python 2.7 (this will take anywhere between 10 and 30 minutes depending
on your computer).

I often invoke py.test explicitly, usually as something like 'PYTHONPATH=src python -m pytest tests/cover/test_testdecorators.py'

There are a number of other tox commands for e.g. running against specific versions of optional dependencies (e.g
tox -e django17 will run the django tests against django 1.7).

The full build will be checked by Travis and Appveyor. Sadly, the tests are very slightly flaky, especially in
the evening (the more of the US who are awake the heavier the load Travis is under, and the flakiness is timing
dependent). Sometimes you'll see one or two build jobs failing for no obvious reason. If you see that and the
failures don't look like anything you've touched, ask me to take a look and I'll tell you if I think it's a real
problem and restart it if not.

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

Of, if you're OK with the pull request but don't feel quite ready to touch the code, you can always
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
* `Charles O'Farrell <https://www.github.com/charleso>`_
* `Christopher Martin <https://www.github.com/chris-martin>`_ (`ch.martin@gmail.com <mailto:ch.martin@gmail.com>`_)
* `Cory Benfield <https://www.github.com/Lukasa>`_
* `Florian Bruhin <https://www.github.com/The-Compiler>`_
* `follower <https://www.github.com/follower>`_
* `Jonty Wareing <https://www.github.com/Jonty>`_ (`jonty@jonty.co.uk <mailto:jonty@jonty.co.uk>`_)
* `kbara <https://www.github.com/kbara>`_
* `marekventur <https://www.github.com/marekventur>`_
* `Marius Gedminas <https://www.github.com/mgedmin>`_ (`marius@gedmin.as <mailto:marius@gedmin.as>`_)
* `Matt Bachmann <https://www.github.com/bachmann1234>`_ (`bachmann.matt@gmail.com <mailto:bachmann.matt@gmail.com>`_)
* `Nicholas Chammas <https://www.github.com/nchammas>`_
* `Richard Boulton <https://www.github.com/rboulton>`_ (`richard@tartarus.org <mailto:richard@tartarus.org>`_)
* `Saul Shanabrook <https://www.github.com/saulshanabrook>`_ (`s.shanabrook@gmail.com <mailto:s.shanabrook@gmail.com>`_)
* `Tariq Khokhar <https://www.github.com/tkb>`_ (`tariq@khokhar.net <mailto:tariq@khokhar.net>`_)
* `Will Hall <https://www.github.com/wrhall>`_ (`wrsh07@gmail.com <mailto:wrsh07@gmail.com>`_)
* `Will Thompson <https://www.github.com/wjt>`_ (`will@willthompson.co.uk <mailto:will@willthompson.co.uk>`_)
