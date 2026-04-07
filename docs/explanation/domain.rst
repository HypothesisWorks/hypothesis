Domain and distribution
=======================

.. note::

    This page is primarily for users who may be familiar with other property-based testing libraries, and who expect control over the distribution of inputs in Hypothesis, via e.g. a ``scale`` parameter for size or a ``frequency`` parameter for relative probabilities.

Hypothesis makes a distinction between the *domain* of a strategy, and the *distribution* of a strategy.

The *domain* is the set of inputs that should be possible to generate. For instance, in ``lists(integers())``, the domain is lists of integers. For other strategies, particularly those that use |st.composite| or |assume| in their definition, the domain might be more complex.

The *distribution* is the probability with which different elements in the domain should be generated. For ``lists(integers())``, should Hypothesis generate many small lists? Large lists? More positive or more negative numbers? etc.

Hypothesis takes a philosophical stance that while users may be responsible for selecting the domain, the property-based testing library—not the user—should be responsible for selecting the distribution. As an intentional design choice, Hypothesis therefore lets you control the domain of inputs to your test, but not the distribution.

How should I choose a domain for my test?
-----------------------------------------

We recommend using the most-general strategy for your test, so that it can in principle generate any edge case for which the test should pass.  Limiting the size of generated inputs, and especially limiting the variety of inputs, can all too easily exclude the bug-triggering values from consideration - and be the difference between a test which finds the bug, or fails to do so.

Sometimes size limits are necessary for performance reasons, but we recommend limiting your strategies only after you've seen *substantial* slowdowns without limits.  Far better to find bugs slowly, than not find them at all - and you can manage performance with the |~settings.phases| or |~settings.max_examples| settings rather than weakening the test.

Why not let users control the distribution?
-------------------------------------------

There are a few reasons Hypothesis doesn't let users control the distribution.

* Humans are pretty bad at choosing bug-finding distributions! Some bugs are "known unknowns": you suspected that a part of the codebase was buggy in a particular way. Others are "unknown unknowns": you didn't know that a bug was possible until stumbling across it. Humans tend to overtune distributions for the former kind of bug, and not enough for the latter.
* The ideal strategy distribution depends not only on the codebase, but also on the property being tested. A strategy used in many places may have a good distribution for one property, but not another.
* The distribution of inputs is a deeply internal implementation detail. We sometimes change strategy distributions, either explicitly, or implicitly from other work on the Hypothesis engine. Exposing this would lock us into a public API that may make improvements to Hypothesis more difficult.

Finally, we think distribution control is better handled with |alternative backends|. If existing backends like ``hypofuzz`` and ``crosshair`` don't suit your needs, you can also write your own. Backends can automatically generalize and adapt to the strategy and property being tested and avoid most of the problems above.

We're not saying that control over the distribution isn't useful! We occasionally receive requests to expose the distribution in Hypothesis (`e.g. <https://github.com/HypothesisWorks/hypothesis/issues/4205>`__), and users wouldn't be asking for it if it wasn't. However, adding this to the public strategy API would make it easy for users to unknowingly weaken their tests, and would add maintenance overhead to Hypothesis, and so we haven't yet done so.

Okay, but what *is* the distribution?
-------------------------------------

An exact answer depends on both the strategy or strategies for the tests, and the code being tested - but we can make some general remarks, starting with "it's actually really complicated".

Hypothesis' default configuration uses a distribution which is tuned to maximize the chance of finding bugs, in as few executions as possible.  We explicitly *don't* aim for a uniform distribution, nor for a 'realistic' distribution of inputs; Hypothesis' goal is to search the domain for a failing input as efficiently as possible.

The test case distribution remains an active area of research and development, and we change it whenever we think that would be a net improvement for users.  Today, Hypothesis' default distribution is shaped by a wide variety of techniques and heuristics:

* some are statically designed into strategies - for example, |st.integers| upweights range endpoints, and samples from a mixed distribution over integer bit-widths.
* some are dynamic features of the engine - like replaying prior examples with subsections of the input 'cloned' or otherwise altered, for bugs which trigger only when different fields have the same value (which is otherwise exponentially unlikely).
* some vary depending on the code under test - we collect interesting-looking constants from imported source files as seeds for test cases.

And as if that wasn't enough, :ref:`alternative backends <alternative-backends>` can radically change the distribution again - for example :pypi:`hypofuzz` uses runtime feedback to modify the distribution of inputs as the test runs, to maximize the rate at which we trigger new behaviors in that particular test and code.  If Hypothesis' defaults aren't strong enough, we recommend trying Hypofuzz!
