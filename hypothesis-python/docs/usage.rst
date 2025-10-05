Projects using Hypothesis
=========================

The following is a non-exhaustive list of open source projects that use Hypothesis to test their code. You can find `thousands more on GitHub <https://github.com/HypothesisWorks/hypothesis/network/dependents>`__.

Hypothesis has `over 8 million downloads per week <https://pypistats.org/packages/hypothesis>`__,
and was used by `more than 5% of Python users surveyed by the PSF in 2023
<https://lp.jetbrains.com/python-developers-survey-2023/>`__.

* `argon2_cffi <https://github.com/hynek/argon2-cffi>`_
* `array-api-tests <https://github.com/data-apis/array-api-tests>`_
* `attrs <https://github.com/python-attrs/attrs>`_
* `axelrod <https://github.com/Axelrod-Python/Axelrod>`_
* `bidict <https://github.com/jab/bidict>`_
* `chardet <https://github.com/chardet/chardet>`_
* `cryptography <https://github.com/pyca/cryptography>`_
* `dry-python/returns <https://github.com/dry-python/returns>`_
* `flocker <https://github.com/ClusterHQ/flocker>`_
* `hyper-h2 <https://github.com/python-hyper/h2>`_
* `ivy <https://github.com/ivy-llc/ivy>`_
* `MDAnalysis <https://github.com/MDAnalysis/mdanalysis>`_
* `mercurial <https://www.mercurial-scm.org/>`_
* `napari <https://github.com/napari/napari>`_
* `natsort <https://github.com/SethMMorton/natsort>`_
* `numpy <https://github.com/numpy/numpy>`_
* `pandas <https://github.com/pandas-dev/pandas>`_
* `pandera <https://github.com/unionai-oss/pandera>`_
* `poliastro <https://github.com/poliastro/poliastro>`_
* `PyPy <https://pypy.org/>`_
* `pyrsistent <https://github.com/tobgu/pyrsistent>`_
* `qutebrowser <https://github.com/qutebrowser/qutebrowser>`_
* `srt <https://github.com/cdown/srt>`_
* `vdirsyncer <https://github.com/pimutils/vdirsyncer>`_
* `xarray <https://github.com/pydata/xarray>`_
* `zenml <https://github.com/zenml-io/zenml>`_

Testimonials
------------

`Stripe <https://stripe.com>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At Stripe we use Hypothesis to test every piece of our machine
learning model training pipeline (powered by scikit). Before we
migrated, our tests were filled with hand-crafted pandas Dataframes
that weren't representative at all of our actual very complex
data. Because we needed to craft examples for each test, we took the
easy way out and lived with extremely low test coverage.

Hypothesis changed all that. Once we had our strategies for generating
Dataframes of features it became trivial to slightly customize each
strategy for new tests. Our coverage is now close to 90%.

Full-stop, property-based testing is profoundly more powerful - and
has caught or prevented far more bugs - than our old style of
example-based testing.

`Seth Morton <https://github.com/SethMMorton>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When I first heard about Hypothesis, I knew I had to include it in my two
open-source Python libraries, `natsort <https://github.com/SethMMorton/natsort>`_
and `fastnumbers <https://github.com/SethMMorton/fastnumbers>`_ . Quite frankly,
I was a little appalled at the number of bugs and "holes" I found in the code. I can
now say with confidence that my libraries are more robust to "the wild." In
addition, Hypothesis gave me the confidence to expand these libraries to fully
support Unicode input, which I never would have had the stomach for without such
thorough testing capabilities. Thanks!

`Sixty North <https://sixty-north.com/>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At Sixty North we use Hypothesis for testing
`Segpy <https://github.com/sixty-north/segpy>`_ an open source Python library for
shifting data between Python data structures and SEG Y files which contain
geophysical data from the seismic reflection surveys used in oil and gas
exploration.

This is our first experience of property-based testing – as opposed to example-based
testing.  Not only are our tests more powerful, they are also much better
explanations of what we expect of the production code. In fact, the tests are much
closer to being specifications.  Hypothesis has located real defects in our code
which went undetected by traditional test cases, simply because Hypothesis is more
relentlessly devious about test case generation than us mere humans!  We found
Hypothesis particularly beneficial for Segpy because SEG Y is an antiquated format
that uses legacy text encodings (EBCDIC) and even a legacy floating point format
we implemented from scratch in Python.

Hypothesis is sure to find a place in most of our future Python codebases and many
existing ones too.

`mulkieran <https://github.com/mulkieran>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just found out about this excellent QuickCheck for Python implementation and
ran up a few tests for my `bytesize <https://github.com/mulkieran/bytesize>`_
package last night. Refuted a few hypotheses in the process.

Looking forward to using it with a bunch of other projects as well.

`Adam Johnson <https://github.com/adamchainz>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I have written a small library to serialize ``dict``\s to MariaDB's dynamic
columns binary format,
`mariadb-dyncol <https://github.com/adamchainz/mariadb-dyncol>`_. When I first
developed it, I thought I had tested it really well - there were hundreds of
test cases, some of them even taken from MariaDB's test suite itself. I was
ready to release.

Lucky for me, I tried Hypothesis with David at the PyCon UK sprints. Wow! It
found bug after bug after bug. Even after a first release, I thought of a way
to make the tests do more validation, which revealed a further round of bugs!
Most impressively, Hypothesis found a complicated off-by-one error in a
condition with 4095 versus 4096 bytes of data - something that I would never
have found.

Long live Hypothesis! (Or at least, property-based testing).

`Josh Bronson <https://github.com/jab>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adopting Hypothesis improved `bidict <https://github.com/jab/bidict>`_'s
test coverage and significantly increased our ability to make changes to
the code with confidence that correct behavior would be preserved.
Thank you, David, for the great testing tool.

`Cory Benfield <https://github.com/Lukasa>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hypothesis is the single most powerful tool in my toolbox for working with
algorithmic code, or any software that produces predictable output from a wide
range of sources. When using it with
`Priority <https://python-hyper.org/projects/priority/en/latest/>`_, Hypothesis consistently found
errors in my assumptions and extremely subtle bugs that would have taken months
of real-world use to locate. In some cases, Hypothesis found subtle deviations
from the correct output of the algorithm that may never have been noticed at
all.

When it comes to validating the correctness of your tools, nothing comes close
to the thoroughness and power of Hypothesis.

`Jon Moore <https://github.com/jonmoore>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One extremely satisfied user here. Hypothesis is a really solid implementation
of property-based testing, adapted well to Python, and with good features
such as failure-case shrinkers. I first used it on a project where we needed
to verify that a vendor's Python and non-Python implementations of an algorithm
matched, and it found about a dozen cases that previous example-based testing
and code inspections had not. Since then I've been evangelizing for it at our firm.

`Russel Winder <https://www.russel.org.uk>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


I am using Hypothesis as an integral part of my Python workshops. Testing is an integral part of Python
programming and whilst unittest and, better, pytest can handle example-based testing, property-based
testing is increasingly far more important than example-base testing, and Hypothesis fits the bill.

`Wellfire Interactive <https://wellfire.co>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We've been using Hypothesis in a variety of client projects, from testing
Django-related functionality to domain-specific calculations. It both speeds
up and simplifies the testing process since there's so much less tedious and
error-prone work to do in identifying edge cases. Test coverage is nice but
test depth is even nicer, and it's much easier to get meaningful test depth
using Hypothesis.

`Cody Kochmann <https://github.com/CodyKochmann>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hypothesis is being used as the engine for random object generation with my
open source function fuzzer
`battle_tested <https://github.com/CodyKochmann/battle_tested>`_
which maps all behaviors of a function allowing you to minimize the chance of
unexpected crashes when running code in production.

With how efficient Hypothesis is at generating the edge cases that cause
unexpected behavior occur,
`battle_tested <https://github.com/CodyKochmann/battle_tested>`_
is able to map out the entire behavior of most functions in less than a few
seconds.

Hypothesis truly is a masterpiece. I can't thank you enough for building it.


`Merchise Autrement <https://github.com/merchise>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just minutes after our first use of hypothesis `we uncovered a subtle bug`__
in one of our most used library.  Since then, we have increasingly used
hypothesis to improve the quality of our testing in libraries and applications
as well.

__ https://github.com/merchise/xotl.tools/commit/0a4a0f529812fed363efb653f3ade2d2bc203945

`Florian Kromer <https://github.com/fkromer>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At `Roboception GmbH <https://roboception.com/>`_ I use Hypothesis to
implement fully automated stateless and stateful reliability tests for the
`3D sensor rc_visard <https://roboception.com/3d-stereo-vision/rc-visard-3d-stereo-sensor/>`_ and
`robotic software components <https://roboception.com/rc-reason-software-suite/>`_ .

Thank you very much for creating the (probably) most powerful property-based
testing framework.

`Reposit Power <https://repositpower.com>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With a micro-service architecture, testing between services is made easy using Hypothesis
in integration testing. Ensuring everything is running smoothly is vital to help maintain
a secure network of Virtual Power Plants.

It allows us to find potential bugs and edge cases with relative ease
and minimal overhead. As our architecture relies on services communicating effectively, Hypothesis
allows us to strictly test for the kind of data which moves around our services, particularly
our backend Python applications.
