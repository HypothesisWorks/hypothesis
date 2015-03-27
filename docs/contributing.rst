------------
Contributing
------------

External contributions to Hypothesis are currently less easy than I would like
them to be. You might want to consider any of the following in preference to
trying to work on the main Hypothesis code base:

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo

And indeed I'll be delighted with you if you do! If you need any help with any
of these, get in touch and I'll be extremely happy to provide it.

However if you really really want to submit code to Hypothesis, the process is
as follows:

You must own the copyright to the patch you're submitting as an individual.
I'm not currently clear on how to accept patches from organisations and other
legal entities.

If you have not already done so, you must sign a CLA assigning copyright to me.
Send an email to hypothesis@drmaciver.com with an attached copy of
`the current version of the CLA <https://github.com/DRMacIver/hypothesis/blob/master/docs/Hypothesis-CLA.pdf?raw=true>`_
and the text in the body "I, (your name), have read the attached CLA and agree
to its terms" (you should in fact have actually read it).

Note that it's important to attach a copy of the CLA because I may change it
from time to time as new things come up and this keeps a record of which
version of it you agreed to.

Then submit a pull request on Github. This will be checked by Travis and
Appveyor to see if the build passes.

Advance warning that passing the build requires:

1. All the tests to pass, naturally.
2. Your code to have 100% branch coverage.
3. Your code to be flake8 clean.
4. Your code to be a fixed point for a variety of reformatting operations (defined in lint.sh)

It is a fairly strict process.

Once all this has happened I'll review your patch. I don't promise to accept
it, but I do promise to review it as promptly as I can and to tell you why if
I reject it.
