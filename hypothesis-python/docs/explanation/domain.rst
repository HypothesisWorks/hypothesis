Domain and distribution
=======================

.. note::

    This page is primarily for users who may be familiar with other property-based testing libraries, and who expect control over the distribution of inputs in Hypothesis, via e.g. a ``scale`` parameter for size or a ``frequency`` parameter for relative probabilities.

Hypothesis makes a distinction between the *domain* of a strategy, and the *distribution* of a strategy.

The *domain* is the set of inputs that should be possible to generate. For instance, in ``lists(integers())``, the domain is lists of integers. For other strategies, particularly those that use |st.composite| or |assume| in their definition, the domain might be more complex.

The *distribution* is the probability with which different elements in the domain should be generated. For ``lists(integers())``, should Hypothesis generate many small lists? Large lists? More positive or more negative numbers? etc.

Hypothesis takes a philosophical stance that while users may be responsible for selecting the domain, the property-based testing library—not the user—should be responsible for selecting the distribution. As an intentional design choice, Hypothesis therefore lets you control the domain of inputs to your test, but not the distribution.

Why not let users control the distribution?
-------------------------------------------

There are a few reasons Hypothesis doesn't let users control the distribution.

* Humans are pretty bad at choosing bug-finding distributions! Some bugs are "known unknowns": you suspected that a part of the codebase was buggy in a particular way. Others are "unknown unknowns": you didn't know that a bug was possible until stumbling across it. Humans tend to overtune distributions for the former kind of bug, and not enough for the latter.
* The ideal strategy distribution depends not only on the codebase, but also on the property being tested. A strategy used in many places may have a good distribution for one property, but not another.
* The distribution of inputs is a deeply internal implementation detail. We sometimes change strategy distributions, either explicitly, or implicitly from other work on the Hypothesis engine. Exposing this would lock us into a public API that may make improvements to Hypothesis more difficult.

Finally, we think distribution control is better handled with :ref:`alternative backends <alternative-backends>`. If existing backends like ``hypofuzz`` and ``crosshair`` don't suit your needs, you can also write your own. Backends can automatically generalize and adapt to the strategy and property being tested and avoid most of the problems above.

We're not saying that control over the distribution isn't useful! We occasionally receive requests to expose the distribution in Hypothesis (`e.g. <https://github.com/HypothesisWorks/hypothesis/issues/4205>`__), and users wouldn't be asking for it if it wasn't. However, adding this to the public strategy API would make it easy for users to unknowingly weaken their tests, and would add maintenance overhead to Hypothesis, and so we haven't yet done so.
