Projects using Hypothesis
=========================

Hypothesis is downloaded `over 4 million times each week <https://pypistats.org/packages/hypothesis>`__,
and was used by `more than 5% of Python users surveyed by the PSF in 2023
<https://lp.jetbrains.com/python-developers-survey-2023/>`__!

The following notable open-source projects use Hypothesis to test their code: `pytorch <https://github.com/pytorch/pytorch>`_, `jax <https://github.com/jax-ml/jax>`_, `PyPy <https://github.com/pypy/pypy>`_, `numpy <https://github.com/numpy/numpy>`_, `pandas <https://github.com/pandas-dev/pandas>`_, `attrs <https://github.com/python-attrs/attrs>`_, `chardet <https://github.com/chardet/chardet>`_, `bidict <https://github.com/jab/bidict>`_, `xarray <https://github.com/pydata/xarray>`_, `array-api-tests <https://github.com/data-apis/array-api-tests>`_, `pandera <https://github.com/unionai-oss/pandera>`_, `ivy <https://github.com/ivy-llc/ivy>`_, `zenml <https://github.com/zenml-io/zenml>`_, `mercurial <https://www.mercurial-scm.org/>`_, `qutebrowser <https://github.com/qutebrowser/qutebrowser>`_, `dry-python/returns <https://github.com/dry-python/returns>`_, `argon2_cffi <https://github.com/hynek/argon2-cffi>`_, `axelrod <https://github.com/Axelrod-Python/Axelrod>`_, `hyper-h2 <https://github.com/python-hyper/h2>`_, `MDAnalysis <https://github.com/MDAnalysis/mdanalysis>`_, `napari <https://github.com/napari/napari>`_, `natsort <https://github.com/SethMMorton/natsort>`_, `vdirsyncer <https://github.com/pimutils/vdirsyncer>`_, and `pyrsistent <https://github.com/tobgu/pyrsistent>`_. You can find `thousands more projects tested by Hypothesis on GitHub <https://github.com/HypothesisWorks/hypothesis/network/dependents>`__.

There are also dozens of :doc:`first-party <extras>` and :doc:`third-party extensions <extensions>` integrating Hypothesis with a wide variety of libraries and data formats.

.. ^ citations that I put effort into looking up but decided not to use. Maybe we'll use them in the future?
.. https://github.com/pytorch/pytorch/blob/59ad8f1ac6bce11617a5f856df9e88b3bf9266af/pyproject.toml#L41
.. https://github.com/jax-ml/jax/blob/48335107f82117ac34c76cac3e22546d2da78eaf/build/test-requirements.txt#L5
.. https://github.com/pypy/pypy/blob/338295bd0567cda9a3c603f428b14229da08e750/extra_tests/requirements.txt#L2
.. https://github.com/numpy/numpy/blob/c9b2919556789675dca0e202dd5a4b46d7d23ff2/requirements/test_requirements.txt#L5
.. https://github.com/pandas-dev/pandas/blob/1863adb252863b718ba29912922bf050ce0eaa3d/pyproject.toml#L60
.. https://github.com/python-attrs/attrs/blob/5084de361bf9e722dda6876e6e2b8ce8c63b7272/pyproject.toml#L47
.. https://github.com/chardet/chardet/blob/8e8dfcd93c572c2cbe37585e01662a90b16fbab6/pyproject.toml#L59
.. https://github.com/jab/bidict/blob/0116e5b772bd2e390267c511187e60931b733153/pyproject.toml#L38
.. https://github.com/pydata/xarray/blob/3572f4e70f2b12ef9935c1f8c3c1b74045d2a092/pyproject.toml#L73
.. https://foss.heptapod.net/mercurial/mercurial-devel/-/blob/b8ca286fda2eb275ffdfd7417fb539a03748d22c/tests/hypothesishelpers.py
.. https://github.com/qutebrowser/qutebrowser/blob/642c5fe2fe46082de53219c19e02fef209753aa0/misc/requirements/requirements-tests.txt#L19

Research papers about Hypothesis
--------------------------------

Looking to read more about Hypothesis and property-based testing? Hypothesis has been the subject of a number of research papers:

1. `Hypothesis: A new approach to property-based testing <https://doi.org/10.21105/joss.01891>`_ (2019)*
2. `Test-Case Reduction via Test-Case Generation: Insights from the Hypothesis Reducer <https://doi.org/10.4230/LIPIcs.ECOOP.2020.13>`_ (2020)*
3. `Deriving semantics-aware fuzzers from web API schemas <https://dl.acm.org/doi/10.1145/3510454.3528637>`_ (2022)*
4. `Tyche: Making Sense of PBT Effectiveness <https://dl.acm.org/doi/10.1145/3654777.3676407>`_ (2024)*
5. `An Empirical Evaluation of Property-Based Testing in Python <https://dl.acm.org/doi/10.1145/3764068>`_ (2025)
6. `Agentic Property-Based Testing: Finding Bugs Across the Python Ecosystem <https://doi.org/10.48550/arXiv.2510.09907>`_ (2025)*

\* *Author list includes one or more Hypothesis maintainers*
