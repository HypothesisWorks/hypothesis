========================
Who is using Hypothesis?
========================

This is a page for listing people who are using Hypothesis and how excited they
are about that. If that's you and your name is not on the list, `this file is in
Git <https://github.com/HypothesisWorks/hypothesis-python/blob/master/docs/endorsements.rst>`_
and I'd love it if you sent me a pull request to fix that.


--------------------------------------------------------------------------------------
Kristian Glass - Director of Technology at `LaterPay GmbH <http://www.laterpay.net/>`_
--------------------------------------------------------------------------------------

Hypothesis has been brilliant for expanding the coverage of our test cases,
and also for making them much easier to read and understand,
so we're sure we're testing the things we want in the way we want.

-----------------------------------------------
`Seth Morton <https://github.com/SethMMorton>`_
-----------------------------------------------

When I first heard about Hypothesis, I knew I had to include it in my two
open-source Python libraries, `natsort <https://github.com/SethMMorton/natsort>`_
and `fastnumbers <https://github.com/SethMMorton/fastnumbers>`_ . Quite frankly,
I was a little appalled at the number of bugs and "holes" I found in the code. I can
now say with confidence that my libraries are more robust to "the wild." In
addition, Hypothesis gave me the confidence to expand these libraries to fully
support Unicode input, which I never would have had the stomach for without such
thorough testing capabilities. Thanks!

-------------------------------------------
`Sixty North <http://sixty-north.com>`_
-------------------------------------------

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

-------------------------------------------
`mulkieran <https://github.com/mulkieran>`_
-------------------------------------------

Just found out about this excellent QuickCheck for Python implementation and
ran up a few tests for my `bytesize <https://github.com/mulkieran/bytesize>`_
package last night. Refuted a few hypotheses in the process.

Looking forward to using it with a bunch of other projects as well.

-----------------------------------------------
`Adam Johnson <https://github.com/adamchainz>`_
-----------------------------------------------

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

-------------------------------------------
`Josh Bronson <https://github.com/jab>`_
-------------------------------------------

Adopting Hypothesis improved `bidict <https://github.com/jab/bidict>`_'s
test coverage and significantly increased our ability to make changes to
the code with confidence that correct behavior would be preserved.
Thank you, David, for the great testing tool.

--------------------------------------------
`Cory Benfield <https://github.com/Lukasa>`_
--------------------------------------------

Hypothesis is the single most powerful tool in my toolbox for working with
algorithmic code, or any software that produces predictable output from a wide
range of sources. When using it with
`Priority <http://python-hyper.org/priority/>`_, Hypothesis consistently found
errors in my assumptions and extremely subtle bugs that would have taken months
of real-world use to locate. In some cases, Hypothesis found subtle deviations
from the correct output of the algorithm that may never have been noticed at
all.

When it comes to validating the correctness of your tools, nothing comes close
to the thoroughness and power of Hypothesis.

------------------------------------------
`Jon Moore <https://github.com/jonmoore>`_
------------------------------------------

One extremely satisfied user here. Hypothesis is a really solid implementation
of property-based testing, adapted well to Python, and with good features
such as failure-case shrinkers. I first used it on a project where we needed
to verify that a vendor's Python and non-Python implementations of an algorithm
matched, and it found about a dozen cases that previous example-based testing
and code inspections had not. Since then I've been evangelizing for it at our firm.

--------------------------------------------
`Russel Winder <https://www.russel.org.uk>`_
--------------------------------------------

I am using Hypothesis as an integral part of my Python workshops. Testing is an integral part of Python
programming and whilst unittest and, better, py.test can handle example-based testing, property-based
testing is increasingly far more important than example-base testing, and Hypothesis fits the bill.

-------------------------------------------
`Your name goes here <http://example.com>`_
-------------------------------------------

I know there are many more, because I keep finding out about new people I'd never
even heard of using Hypothesis. If you're looking to way to give back to a tool you
love, adding your name here only takes a moment and would really help a lot. As per
instructions at the top, just send me a pull request and I'll add you to the list.
