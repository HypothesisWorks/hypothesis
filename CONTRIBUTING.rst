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
* django will just run tests for the django integration
* pytest will just run tests for the pytest plugin

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
* `Jonty Wareing <https://www.github.com/Jonty>`_ (`jonty@jonty.co.uk <mailto:jonty@jonty.co.uk>`_)
* `kbara <https://www.github.com/kbara>`_
* `Lee Begg <https://www.github.com/llnz2>`_
* `marekventur <https://www.github.com/marekventur>`_
* `Marius Gedminas <https://www.github.com/mgedmin>`_ (`marius@gedmin.as <mailto:marius@gedmin.as>`_)
* `Markus Unterwaditzer <http://github.com/untitaker/>`_ (`markus@unterwaditzer.net <mailto:markus@unterwaditzer.net>`_)
* `Matt Bachmann <https://www.github.com/bachmann1234>`_ (`bachmann.matt@gmail.com <mailto:bachmann.matt@gmail.com>`_)
* `Nicholas Chammas <https://www.github.com/nchammas>`_
* `Richard Boulton <https://www.github.com/rboulton>`_ (`richard@tartarus.org <mailto:richard@tartarus.org>`_)
* `Saul Shanabrook <https://www.github.com/saulshanabrook>`_ (`s.shanabrook@gmail.com <mailto:s.shanabrook@gmail.com>`_)
* `Tariq Khokhar <https://www.github.com/tkb>`_ (`tariq@khokhar.net <mailto:tariq@khokhar.net>`_)
* `Will Hall <https://www.github.com/wrhall>`_ (`wrsh07@gmail.com <mailto:wrsh07@gmail.com>`_)
* `Will Thompson <https://www.github.com/wjt>`_ (`will@willthompson.co.uk <mailto:will@willthompson.co.uk>`_)
