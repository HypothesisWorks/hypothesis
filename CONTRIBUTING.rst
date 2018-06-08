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
(don't worry, we'll help you through it), so do read the rest of this document.
If you're planning a larger change, the contributor guides (in the ``guides/``
directory) will make sure you're on the right track.

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

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pull request or external package?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New strategies can be added to Hypothesis, or published as an external package
on PyPI - either is fine for most strategies.  If in doubt, ask!

It's generally much easier to get things working outside, because there's
more freedom to experiment and fewer requirements in stability and API style.
We're happy to review and help with external packages as well as pull requests;
several parts of Hypothesis started life outside and were integrated later
(with permission, of course).  For clarity, we suggest naming your package
in the pattern of ``hypothesis-regex`` and ``hypothesis-protobuf`` on PyPI.

On the other hand, being inside gets you access to some deeper implementation
features (if you need them) and better long-term guarantees about maintenance.
We particularly encourage pull requests for new composable primitives that
make implementing other strategies easier, or for widely used types in the
Python standard library.  Strategies for other things are also welcome;
anything with external dependencies just goes in ``hypothesis.extra``.

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

You can also run a number of finer grained make tasks - check ``.travis.yml`` for a short list and
the Makefile for details.

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
* `Alex Willmer <https://github.com/moreati>`_ (alex@moreati.org.uk)
* `Ben Peterson <https://github.com/killthrush>`_ (killthrush@hotmail.com)
* `Buck Evan, copyright Google LLC <https://github.com/bukzor>`_
* `Charles O'Farrell <https://www.github.com/charleso>`_
* `Charlie Tanksley <https://www.github.com/charlietanksley>`_
* `Chase Garner <https://www.github.com/chasegarner>`_ (chase@garner.red)
* `Chris Down  <https://chrisdown.name>`_
* `Christopher Martin <https://www.github.com/chris-martin>`_ (ch.martin@gmail.com)
* `Conrad Ho <https://www.github.com/conradho>`_ (conrad.alwin.ho@gmail.com)
* `Cory Benfield <https://www.github.com/Lukasa>`_
* `Cristi Cobzarenco <https://github.com/cristicbz>`_ (cristi@reinfer.io)
* `David Bonner <https://github.com/rascalking>`_ (dbonner@gmail.com)
* `David Chudzicki <https://github.com/dchudz>`_ (dchudz@gmail.com)
* `Derek Gustafson <https://www.github.com/degustaf>`_
* `Dion Misic <https://www.github.com/kingdion>`_ (dion.misic@gmail.com)
* `Florian Bruhin <https://www.github.com/The-Compiler>`_
* `follower <https://www.github.com/follower>`_
* `Grant David Bachman <https://github.com/grantbachman>`_ (grantbachman@gmail.com)
* `Gregory Petrosyan <https://github.com/flyingmutant>`_
* `Jeremy Thurgood <https://github.com/jerith>`_
* `J.J. Green <http://soliton.vm.bytemark.co.uk/pub/jjg/>`_
* `JP Viljoen <https://github.com/froztbyte>`_ (froztbyte@froztbyte.net)
* `Jonty Wareing <https://www.github.com/Jonty>`_ (jonty@jonty.co.uk)
* `jwg4 <https://www.github.com/jwg4>`_
* `kbara <https://www.github.com/kbara>`_
* `Kyle Reeve <https://www.github.com/kreeve>`_ (krzw92@gmail.com)
* `Lee Begg <https://www.github.com/llnz2>`_
* `Louis Taylor <https://github.com/kragniz>`_
* `marekventur <https://www.github.com/marekventur>`_
* `Marius Gedminas <https://www.github.com/mgedmin>`_ (marius@gedmin.as)
* `Markus Unterwaditzer <http://github.com/untitaker/>`_ (markus@unterwaditzer.net)
* `Matt Bachmann <https://www.github.com/bachmann1234>`_ (bachmann.matt@gmail.com)
* `Max Nordlund <https://www.github.com/maxnordlund>`_ (max.nordlund@gmail.com)
* `Maxim Kulkin <https://www.github.com/maximkulkin>`_ (maxim.kulkin@gmail.com)
* `mulkieran <https://www.github.com/mulkieran>`_
* `Nicholas Chammas <https://www.github.com/nchammas>`_
* `Peadar Coyle <http://www.github.com/springcoil>`_ (peadarcoyle@gmail.com)
* `Richard Boulton <https://www.github.com/rboulton>`_ (richard@tartarus.org)
* `Sam Hames <https://www.github.com/SamHames>`_
* `Saul Shanabrook <https://www.github.com/saulshanabrook>`_ (s.shanabrook@gmail.com)
* `Tariq Khokhar <https://www.github.com/tkb>`_ (tariq@khokhar.net)
* `Will Hall <https://www.github.com/wrhall>`_ (wrsh07@gmail.com)
* `Will Thompson <https://www.github.com/wjt>`_ (will@willthompson.co.uk)
* `Zac Hatfield-Dodds <https://www.github.com/Zac-HD>`_ (zac.hatfield.dodds@gmail.com)
