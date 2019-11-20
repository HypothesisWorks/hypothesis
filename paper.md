---
title: 'Hypothesis: A new approach to property-based testing'
date: 1 November 2019
bibliography: paper.bib
tags:
    - Python
    - testing
    - test-case reduction
    - test-case generation
    - property-based testing
authors:
    - name: David R. MacIver
      orcid: 0000-0002-8635-3223
      affiliation: 1
    - name: Zac Hatfield-Dodds
      orcid: 0000-0002-8646-8362
      affiliation: 2
    - name: many other contributors
      affiliation: 3
affiliations:
    - name: Imperial College London
      index: 1
    - name: Australian National University
      index: 2
    - name: Various
      index: 3
---

# Summary

*Property-based testing* is a style of testing popularised by the QuickCheck family of libraries,
first in Haskell [@DBLP:conf/icfp/ClaessenH00] and later in Erlang [@DBLP:conf/erlang/ArtsHJW06],
which integrates generated test cases into existing software testing workflows:
Instead of tests that provide examples of a single concrete behaviour,
tests specify properties that hold for a wide range of inputs,
which the testing library then attempts to generate test cases to refute.
For a general introduction to property-based testing, see [@PraiseOfPBT].

Hypothesis is a mature and widely used property-based testing library for Python.
It has over 100,000 downloads per week^[https://pypistats.org/packages/hypothesis], thousands of open source projects use it^[https://github.com/HypothesisWorks/hypothesis/network/dependents],
and in 2018 more than 4% of Python users surveyed by the PSF reported using it^[https://www.jetbrains.com/research/python-developers-survey-2018/].
It will be of interest both to researchers using Python for developing scientific software,
and to software testing researchers as a platform for research in its own right.

# Hypothesis for Testing Scientific Software

Python has a rich and thriving ecosystem of scientific software, and Hypothesis is helpful for ensuring its correctness.
Any researcher who tests their software in Python can benefit from these facilities,
but it is particularly useful for improving the correctness foundational libraries on which the scientific software ecosystem is built.
For example, it has found bugs in astropy [@astropy:2018]^[e.g. https://github.com/astropy/astropy/pull/9328, https://github.com/astropy/astropy/pull/9532] and numpy [@DBLP:journals/cse/WaltCV11]^[e.g. https://github.com/numpy/numpy/issues/10930, https://github.com/numpy/numpy/issues/13089, https://github.com/numpy/numpy/issues/14239].

Additionally, Hypothesis is easily extensible, and has a number of third-party extensions for specific research applications.
For example, hypothesis-networkx^[https://pypi.org/project/hypothesis-networkx/] generates graph data structures,
and hypothesis-bio^[https://pypi.org/project/hypothesis-bio/] generates formats suitable for bioinformatics.
As it is used by more researchers, the number of research applications will only increase.

By lowering the barrier to effective testing, Hypothesis makes testing of research software written in Python much more compelling,
and has the potential to significantly improve the quality of the associated scientific research as a result.

# Hypothesis for Software Testing Research

Hypothesis is a powerful platform for software testing research,
both because of the wide array of software that can be easily tested with it,
and because it has a novel implementation that solves a major difficulty faced by prior software testing research.

Much of software testing research boils down to variants on the following problem:
Given some interestingness condition (e.g., that it triggers a bug in some software),
how do we generate a "good" test case that satisfies that condition?

Particular sub-problems of this are:

1. How do we generate test cases that satisfy difficult interestingness conditions?
2. How do we ensure we generate only valid test cases? (the *test-case validity problem* - see @DBLP:conf/pldi/RegehrCCEEY12)
3. How do we generate human readable test cases?

Traditionally property-based testing has adopted random test-case generation to find interesting test cases,
followed by test-case reduction (see @DBLP:conf/pldi/RegehrCCEEY12, @DBLP:journals/tse/ZellerH02) to turn them into more human readable ones,
requiring the users to manually specify a *validity oracle* (a predicate that identifies if an arbitrary test case is valid) to avoid invalid test cases.

The chief limitations of this from a user's point of view are:

* Writing correct validity oracles is difficult and annoying.
* Random generation, while often much better than hand-written examples, is not especially good at satisfying difficult properties.
* Writing test-case reducers that work well for your problem domain is a specialised skill that few people have or want to acquire.

The chief limitation from a researcher's point of view is that trying to improve on random generation's ability to find bugs will typically require modification of existing tests to support new ways of generating data,
and typically these modifications are significantly more complex than writing the random generator would have been.
Users are rarely going to be willing to undertake the work themselves,
which leaves researchers in the unfortunate position of having to put in a significant amount of work per project to understand how to test it.

Hypothesis avoids both of these problems by using a single universal representation for test cases.
Ensuring that test cases produced from this format are valid is relatively easy, no more difficult than ensuring that randomly generated tests cases are valid,
and improvements to the generation process can operate solely on this universal representation rather than requiring adapting to each test.

Currently Hypothesis uses this format to support two major use cases:

1. It is the basis of its approach to test-case reduction, allowing it to support more powerful test-case reduction than is found in most property-based testing libraries with no user intervention.
2. It supports Targeted Property-Based Testing [@DBLP:conf/issta/LoscherS17], which uses a score to guide testing towards a particular goal (e.g., maximising an error term). In the original implementation this would require custom mutation operators per test,
   but in Hypothesis this mutation is transparent to the user and they need only specify the goal.

The internal format is flexible and contains rich information about the structure of generated test cases,
so it is likely future versions of the software will see other features built on top of it,
and we hope researchers will use it as a vehicle to explore other interesting possibilities for test-case generation.

# References
