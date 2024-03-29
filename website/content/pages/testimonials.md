---
title: Testimonials
date: 2015-04-25 22:03
---

<blockquote class="testimonial blockquote-reverse pull" id='alex-stapleton'>
<p>
Hypothesis is easy to learn and powerful implementation of property based testing,
and generally an invaluable tool. At Lyst we've used it in a wide variety of
situations, from testing APIs to machine learning algorithms and in all
cases it's given us a great deal more confidence in that code.
</p>
<footer>Alex Stapleton, Lead Backend Engineer at <a href="https://www.lyst.com/">Lyst</a></footer></cite>
</blockquote>

<blockquote class="testimonial blockquote-reverse pull" id='cory-benfield'>
<p>
Hypothesis is the single most powerful tool in my toolbox for working with
algorithmic code, or any software that produces predictable output from a wide
range of sources. When using it with <a href="http://python-hyper.org/priority/">Priority</a>, Hypothesis consistently found
errors in my assumptions and extremely subtle bugs that would have taken months
of real-world use to locate. In some cases, Hypothesis found subtle deviations
from the correct output of the algorithm that may never have been noticed at
all.
</p>
<p>
When it comes to validating the correctness of your tools, nothing comes close
to the thoroughness and power of Hypothesis.
</p>
 <footer><a href="https://github.com/Lukasa">Cory Benfield</a></footer></cite>
</blockquote>

<blockquote class="testimonial blockquote-reverse pull" id='kristian-glass'>
<p>Hypothesis has been brilliant for expanding the coverage of our test cases,
and also for making them much easier to read and understand,
so we're sure we're testing the things we want in the way we want.</p>
 <footer><a href="/testimonials/#kristian-glass">Kristian Glass</a>, Director of Technology at <a href="https://www.laterpay.net/">LaterPay</a></footer></cite>
</blockquote>

<blockquote class="testimonial blockquote-reverse pull" id='sixty-north'>
<p>
At Sixty North we use Hypothesis for testing
<a href="https://github.com/sixty-north/segpy">Segpy</a>, an open source Python library for
shifting data between Python data structures and SEG Y files which contain
geophysical data from the seismic reflection surveys used in oil and gas
exploration.</p>

<p>This is our first experience of property-based testing – as opposed to example-based
testing.  Not only are our tests more powerful, they are also much better
explanations of what we expect of the production code. In fact, the tests are much
closer to being specifications.  Hypothesis has located real defects in our code
which went undetected by traditional test cases, simply because Hypothesis is more
relentlessly devious about test case generation than us mere humans!  We found
Hypothesis particularly beneficial for Segpy because SEG Y is an antiquated format
that uses legacy text encodings (EBCDIC) and even a legacy floating point format
we implemented from scratch in Python.</p>

<p>
Hypothesis is sure to find a place in most of our future Python codebases and many
existing ones too.
</p>
 <footer>Rob Smallshire, <a href="http://sixty-north.com/">Sixty North</a></footer></cite>
</blockquote>


<blockquote class="testimonial blockquote-reverse pull" id='seth-morton'>
<p>
When I first heard about Hypothesis, I knew I had to include it in my two
open-source Python libraries, <a href="https://github.com/SethMMorton/natsort">natsort</a>
and <a href="https://github.com/SethMMorton/fastnumbers">fastnumbers</a>.</p>

<p>Quite frankly,
I was a little appalled at the number of bugs and "holes" I found in the code. I can
now say with confidence that my libraries are more robust to "the wild." In
addition, Hypothesis gave me the confidence to expand these libraries to fully
support Unicode input, which I never would have had the stomach for without such
thorough testing capabilities. Thanks!
</p>

 <footer><a href="https://github.com/SethMMorton">Seth Morton</a></footer></cite>

</blockquote>

<blockquote class="testimonial blockquote-reverse pull" id='mulkieran'>
<p>
Just found out about this excellent QuickCheck for Python implementation and
ran up a few tests for my <a href="https://github.com/mulkieran/bytesize">bytesize</a>
package last night. Refuted a few hypotheses in the process.
</p>

<p>
Looking forward to using it with a bunch of other projects as well.
</p>
<footer>
<a href="https://github.com/mulkieran">mulkieran</a>
</footer>
</blockquote>


<blockquote class="testimonial blockquote-reverse pull" id='adam-johnson'>
<p> I have written a small library to serialize dicts to MariaDB's dynamic columns binary format, <a href=https://github.com/adamchainz/mariadb-dyncol">mariadb-dyncol</a>. When I first
developed it, I thought I had tested it really well - there were hundreds of
test cases, some of them even taken from MariaDB's test suite itself. I was
ready to release.
</p>

<p>
Lucky for me, I tried Hypothesis with David at the PyCon UK sprints. Wow! It
found bug after bug after bug. Even after a first release, I thought of a way
to make the tests do more validation, which revealed a further round of bugs!
Most impressively, Hypothesis found a complicated off-by-one error in a
condition with 4095 versus 4096 bytes of data - something that I would never
have found.
</p>
<p>
Long live Hypothesis! (Or at least, property-based testing).
</p>
<footer>
<a href="https://github.com/adamchainz">Adam Johnson</a>
</footer>
</blockquote>

<blockquote class="testimonial blockquote-reverse pull" id='adam-johnson'>
<p>
Adopting Hypothesis improved <a href="https://github.com/jab/bidict">bidict</a>'s
test coverage and significantly increased our ability to make changes to
the code with confidence that correct behavior would be preserved.
Thank you, David, for the great testing tool.
</p>
<footer>
<a href="https://github.com/jab">Josh Bronson</a>
</footer>
</blockquote>


<blockquote class="testimonial blockquote-reverse pull" id='jon-moore'>
<p>
One extremely satisfied user here. Hypothesis is a really solid implementation
of property-based testing, adapted well to Python, and with good features
such as failure-case shrinkers. I first used it on a project where we needed
to verify that a vendor's Python and non-Python implementations of an algorithm
matched, and it found about a dozen cases that previous example-based testing
and code inspections had not. Since then I've been evangelizing for it at our firm.
</p>
<footer>
<a href="https://github.com/jonmoore">Jon Moore</a>
</footer>
</blockquote>

<h3>Your name goes here</h3>
<p>
Want to add to the list by telling us about your Hypothesis experience? Drop us
an email at <a href="mailto:testimonials@hypothesis.works">testimonials@hypothesis.works</a>
and we'll add it to the list!
</p>
<p>

</p>