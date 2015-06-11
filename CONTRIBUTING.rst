============
Contributing
============

External contributions to Hypothesis are currently less easy than I would like
them to be. You might want to consider any of the following in preference to
trying to work on the main Hypothesis code base:

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo

And indeed I'll be delighted with you if you do! If you need any help with any
of these, get in touch and I'll be extremely happy to provide it.

If however you're feeling really keen and you still want to contribute, go for
it. It's certainly a lot easier than it used to be. You might find it easier to
start with one of the extra packages (hypothesis-django could sure use some love
from someone who knows Django better than I do), but whatever you do the process
is the same.

-----------------------
Copyright and Licensing
-----------------------

First, make sure that you own the rights to the work you are submitting. If it
is done on work time, or you have a particularly onerous contract, make sure
you've checked with your employer.

All work in Hypothesis is licensed under the terms of the
`Mozilla Public License, version 2.0 <http://mozilla.org/MPL/2.0/>`_. By
submitting a contribution you are agreeing to licence your work under those
terms.

Finally, if it is not there already, add your name (and a link to your github
and email address if you want) account to the list of contributors found at
the end of this document, in alphabetical order. It doesn't have to be your
"real" name (whatever that means), any sort of publical identifier
is fine. In particular a Github account is sufficient.

-----------------------
The actual contribution
-----------------------

Then submit a pull request on Github. This will be checked by Travis and
Appveyor to see if the build passes.

Advance warning that passing the build requires:

1. All the tests to pass, naturally.
2. Your code to have 100% branch coverage.
3. Your code to be flake8 clean.
4. Your code to be a fixed point for a variety of reformatting operations (defined in lint.sh)

Note: The build is a bit flaky because of the number of build jobs. Sorry about that. If a
job fails and you can't understand why, try rerunning it. I'm trying to make this better, but
it's an ongoing battle.

Once all this has happened I'll review your patch. I don't promise to accept
it, but I do promise to review it as promptly as I can and to tell you why if
I reject it.

--------------------
List of Contributors
--------------------

The primary author for most of Hypothesis is David R. MacIver (me). However the following

people have also contributed work. As well as my thanks, they also have copyright over
their individual contributions.

* `Adam Sven Johnson <https://www.github.com/pkqk>`_
* `Alex Stapleton <https://www.github.com/public>`_ 
* `Charles O'Farrell <https://www.github.com/charleso>`_ 
* `Christopher Martin <https://www.github.com/chris-martin>`_ (`ch.martin@gmail.com <mailto:ch.martin@gmail.com>`_)
* `follower <https://www.github.com/follower>`_
* `Jonty Wareing <https://www.github.com/Jonty>`_ (`jonty@jonty.co.uk <mailto:jonty@jonty.co.uk>`_)
* `kbara <https://www.github.com/kbara>`_
* `marekventur <https://www.github.com/marekventur>`_
* `Marius Gedminas <https://www.github.com/mgedmin>`_ (`marius@gedmin.as <mailto:marius@gedmin.as>`_)
* `Nicholas Chammas <https://www.github.com/nchammas>`_
* `Richard Boulton <https://www.github.com/rboulton>`_ (`richard@tartarus.org <mailto:richard@tartarus.org>`_)
* `Saul Shanabrook <https://www.github.com/saulshanabrook>`_ (`s.shanabrook@gmail.com <mailto:s.shanabrook@gmail.com>`_)
* `Tariq Khokhar <https://www.github.com/tkb>`_ (`tariq@khokhar.net <mailto:tariq@khokhar.net>`_)
* `Will Hall <https://www.github.com/wrhall>`_ (`wrsh07@gmail.com <mailto:wrsh07@gmail.com>`_)
* `Will Thompson <https://www.github.com/wjt>`_ (`will@willthompson.co.uk <mailto:will@willthompson.co.uk>`_)
