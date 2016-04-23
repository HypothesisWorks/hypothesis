---
title: Most testing is ineffective
layout: page
date: 2015-04-23 22:03
---

Normal "automated" software testing is surprisingly manual. Every scenario the computer runs, a developer had to
write by hand. Hypothesis can fix this.

Hypothesis is a new generation of tools for automating your testing process. It combines human understanding of
your problem domain with machine intelligence to improve the quality of your testing process while spending
*less* time writing tests.

Don't believe us? Here's what some of our users have to say:

<blockquote class="blockquote-reverse pull">
When it comes to validating the correctness of your tools, nothing comes close to the thoroughness and power of Hypothesis.

 <footer><a href="https://hypothesis.readthedocs.org/en/latest/endorsements.html#id6">Cory Benfield</a>, <a href="https://github.com/Lukasa">Open source Python developer</a></footer></cite>
</blockquote>


<blockquote class="blockquote-reverse pull">
Hypothesis has been brilliant for expanding the coverage of our test cases, and also for making them much easier to read and understand, so we’re sure we’re testing the things we want in the way we want.
 <footer><a href="https://hypothesis.readthedocs.org/en/latest/endorsements.html#kristian-glass-director-of-technology-at-laterpay-gmbh">Kristian Glass</a>, <a href="https://www.laterpay.net/">LaterPay</a></footer></cite>
</blockquote>

<blockquote class="blockquote-reverse pull">
Hypothesis has located real defects in our code which went undetected by traditional test cases, simply because Hypothesis is more relentlessly devious about test case generation than us mere humans!
 <footer><a href="https://hypothesis.readthedocs.org/en/latest/endorsements.html#id2">Rob Smallshire</a>, <a href="http://sixty-north.com/">Sixty North</a></footer></cite>
</blockquote>

## What is Hypothesis?

Hypothesis is a modern implementation of [property based testing](https://en.wikipedia.org/wiki/QuickCheck), designed from the ground up for mainstream languages.

Hypothesis runs your tests against a much wider range of scenarios than a human tester could, finding edge cases
in your code that you would otherwise have missed. It then turns them into simple and easy to understand failures
that save you time and money compared to fixing them if they slipped through the cracks and a user had run into
them instead.

Hypothesis currently has [a fully featured open source Python implementation](https://github.com/HypothesisWorks/hypothesis-python/) and [a proof of concept Java implementation](https://github.com/HypothesisWorks/hypothesis-java) that we are looking for customers to partner with to turn into a finished project.
Plans for C and C++ support are also in the works.

## How do I use it?

Hypothesis integrates into your normal testing workflow. Getting started is as simple as installing a library and
writing some code using it - no new services to run, no new test runners to learn.

Right now only the Python version of Hypothesis is production ready. To get started with it, check out
[the documentation](https://hypothesis.readthedocs.org/en/latest/) or read some of the
[introductory articles here on this site](/articles/intro/).

Once you've got started, or if you have a large number of people who want to get started all at once,
you may wish to engage [our training services](/training).

If you still want to know more, sign up to our newsletter to get an email every 1-2 weeks about the latest and greatest Hypothesis developments and how to test your software better.

<form id="tinyletter" action="https://tinyletter.com/DRMacIver" method="post" target="popupwindow" onsubmit="window.open('https://tinyletter.com/DRMacIver', 'popupwindow', 'scrollbars=yes,width=800,height=600'); return true;"><input type="email" name="email" id="tlemail" placeholder="Your email address"/><input type="hidden" value="1" name="embed" /><input type="submit" value="Subscribe"/></form>
