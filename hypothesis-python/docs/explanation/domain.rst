Domain and distribution
=======================

.. note::

    This page is mainly for users who are familiar with other property-based testing libraries, and who expect a way to control the distribution of inputs in Hypothesis, via e.g. a scale parameter for size or a frequency parameter for relative probabilities.

Hypothesis makes a distinction between the *domain* of a strategy, and the *distribution* of a strategy.

* The domain is the set of inputs that should be possible to generate. For instance, in ``lists(integers())``, the domain is lists of integers. For other strategies, particularly those that use |st.composite| or |assume| in their definition, the domain might be more complex.
* The distribution is the probability with which different elements in the domain should be generated. For ``lists(integers())``, should Hypothesis generate many small lists? Large lists? More positive or more negative numbers? etc.

Hypothesis takes a philosophical stance that property-based testing libraries should be responsible for selecting the distribution; not the user. As an intentional design choice, Hypothesis therefore lets you control the domain of inputs to your test, but not the distribution.

There are a few reasons for this:

* Humans are pretty bad at choosing bug-finding distributions! Some bugs are "known unknowns": you had a good idea that some part of the code was buggy in a particular way. Others are "unknown unknowns": you had no idea that a certain kind of bug was even possible until you stumbled across it. Humans tend to overtune distributions for the former kind of bug, and not enough for the latter.
* The distribution of inputs is a deeply internal implementation detail. We frequently make changes to the distributions of strategies, either in an explicit change for that strategy, or as an implicit consequence from other work on the Hypothesis engine. Exposing control over the distribution would lock us into a public API that may make improvements to Hypothesis more difficult.

We're not saying that control over the distribution isn't useful! We occasionally receive requests to expose the distribution in Hypothesis (`e.g. <https://github.com/HypothesisWorks/hypothesis/issues/4205>`__), and users wouldn't be asking for it if it wasn't.

However, adding this would make it easy for users to unknowingly weaken their tests and would add maintenance overhead to Hypothesis, and so we haven't yet done so.
