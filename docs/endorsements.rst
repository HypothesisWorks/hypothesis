========================
Who is using Hypothesis?
========================

This is a page for listing people who are using Hypothesis and how excited they
are about that. If that's you and your name is not on the list, `this file is in
Git <https://github.com/DRMacIver/hypothesis/blob/master/docs/endorsements.rst>`_
and I'd love it if you sent me a pull request to fix that.


--------------------------------------------
`Kristian Glass <http://www.laterpay.net/>`_
--------------------------------------------

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
`Your name goes here <http://example.com>`_
-------------------------------------------

I know there are many more, because I keep finding out about new people I'd never
even heard of using Hypothesis. If you're looking to way to give back to a tool you
love, adding your name here only takes a moment and would really help a lot. As per
instructions at the top, just send me a pull request and I'll add you to the list.
