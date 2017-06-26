=============
Contributing
=============

First off: It's great that you want to contribute to Hypothesis! Thanks!

------------------
Ways to Contribute
------------------

Hypothesis is a mature yet active project. This means that there are many
ways in which you can contribute.

For example, it's super useful and highly appreciated if you do any of:

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Give a talk about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo
* Submit PRs

If you build a Hypothesis strategy that you would like to be more widely known
please add it to the list of external strategies by preparing a PR against
the docs/strategies.rst file.

If you find an error in the documentation, please feel free to submit a PR that
fixes the error. Spot a tyop? Fix it up and send us a PR!
You can read more about how we document Hypothesis in ``guides/documentation.rst``

The process for submitting source code PRs is generally more involved
(don't worry, we'll help you through it), so do read the rest of this document
first.

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

First off: If you're planning on implementing a new feature, talk to us
first! Come `join us on IRC <https://hypothesis.readthedocs.io/en/latest/community.html#community>`_,
or open an issue. If it's really small feel free to open a work in progress pull request sketching
out the idea, but it's best to get feedback from the Hypothesis maintainers
before sinking a bunch of work into it.

In general work-in-progress pull requests are totally welcome if you want early feedback
or help with some of the tricky details. Don't be afraid to ask for help.

In order to get merged, a pull request will have to have a green build (naturally) and
to be approved by a Hypothesis maintainer (and, depending on what it is, possibly specifically
by DRMacIver).

The review process is the same one that all changes to Hypothesis go through, regardless of
whether you're an established maintainer or entirely new to the project. It's very much
intended to be a collaborative one: It's not us telling you what we think is wrong with
your code, it's us working with you to produce something better together.

We have `a lengthy check list <guides/review.rst>`_ of things we look for in a review. Feel
free to have a read of it in advance and go through it yourself if you'd like to. It's not
required, but it might speed up the process.

Once your pull request has a green build and has passed review, it will be merged to
master fairly promptly. This will immediately trigger a release! Don't be scared. If that
breaks things, that's our fault not yours - the whole point of this process is to ensure
that problems get caught before we merge rather than after.


~~~~~~~~~~~~~~~~
The Release File
~~~~~~~~~~~~~~~~

All changes to Hypothesis get released automatically when they are merged to
master.

In order to update the version and change log entry, you have to create a
release file. This is a normal restructured text file called RELEASE.rst that
lives in the root of the repository and will be used as the change log entry.

It should start with following lines:

* RELEASE_TYPE: major
* RELEASE_TYPE: minor
* RELEASE_TYPE: patch

This specifies the component of the version number that should be updated, with
the meaning of each component following `semver <http://semver.org/>`_. As a
rule of thumb if it's a bug fix it's probably a patch version update, if it's
a new feature it's definitely a minor version update, and you probably
shouldn't ever need to use a major version update unless you're part of the
core team and we've discussed it a lot.

This line will be removed from the final change log entry.

~~~~~~~~~
The build
~~~~~~~~~

The build is orchestrated by a giant Makefile which handles installation of the relevant pythons.
Actually running the tests is managed by `tox <https://tox.readthedocs.io/en/latest/>`_, but the Makefile
will call out to the relevant tox environments so you mostly don't have to know anything about that
unless you want to make changes to the test config. You also mostly don't need to know anything about make
except to type 'make' followed by the name of the task you want to run.

All of it will be checked on CI so you don't *have* to run anything locally, but you might
find it useful to do so: A full Travis run takes about twenty minutes, and there's often a queue,
so running a smaller set of tests locally can be helpful.

The makefile should be "fairly" portable, but is currently only known to work on Linux or OS X. It *might* work
on a BSD or on Windows with cygwin installed, but it hasn't been tried. If you try it and find it doesn't
work, please do submit patches to fix that.

Some notable commands:

'make format' will reformat your code according to the Hypothesis coding style. You should use this before each
commit ideally, but you only really have to use it when you want your code to be ready to merge.

You can also use 'make check-format', which will run format and some linting and will then error if you have a
git diff. Note: This will error even if you started with a git diff, so if you've got any uncommitted changes
this will necessarily report an error.

'make check' will run check-format and all of the tests. Warning: This will take a *very* long time. On Travis the
build currently takes more than an hour of total time (it runs in parallel on Travis so you don't have to wait
quite that long). If you've got a multi-core machine you can run 'make -j 2' (or any higher number if you want
more) to run 2 jobs in parallel, but to be honest you're probably better off letting Travis run this step.

You can also run a number of finer grained make tasks:

* check-fast runs a fast but reasonably comprehensive subset of make check. It's still not *that* fast, but it
  takes a couple of minutes instead of a couple of hours.
* You can run the tests just for a single version of Python using one of check-py26, check-py27, check-py34,
  check-py35, check-pypy.
* check-coverage will run a subset of the tests on python 3.5 and then assert that this gave 100% coverage
* lint will just run some source code checks.
* check-django will just run tests for the Django integration
* check-pytest will just run tests for the pytest plugin

Note: The build requires a lot of different versions of python, so rather than have you install them yourself,
the makefile will install them itself in a local directory. This means that the first time you run a task you
may have to wait a while as the build downloads and installs the right version of python for you.

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
* `Ben Peterson <https://github.com/killthrush>`_ (`killthrush@hotmail.com <mailto:killthrush@hotmail.com>`_)
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
* `Maxim Kulkin <https://www.github.com/maximkulkin>`_ (`maxim.kulkin@gmail.com <mailto:maxim.kulkin@gmail.com>`_)
* `mulkieran <https://www.github.com/mulkieran>`_
* `Nicholas Chammas <https://www.github.com/nchammas>`_
* `Richard Boulton <https://www.github.com/rboulton>`_ (`richard@tartarus.org <mailto:richard@tartarus.org>`_)
* `Saul Shanabrook <https://www.github.com/saulshanabrook>`_ (`s.shanabrook@gmail.com <mailto:s.shanabrook@gmail.com>`_)
* `Tariq Khokhar <https://www.github.com/tkb>`_ (`tariq@khokhar.net <mailto:tariq@khokhar.net>`_)
* `Will Hall <https://www.github.com/wrhall>`_ (`wrsh07@gmail.com <mailto:wrsh07@gmail.com>`_)
* `Will Thompson <https://www.github.com/wjt>`_ (`will@willthompson.co.uk <mailto:will@willthompson.co.uk>`_)
* `Zac Hatfield-Dodds <https://www.github.com/Zac-HD>`_ (`zac.hatfield.dodds@gmail.com <mailto:zac.hatfield.dodds@gmail.com>`_)
