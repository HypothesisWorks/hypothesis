RELEASE_TYPE: patch

Improve the thread-safety of strategy validation.

Before this release, Hypothesis did not require that ``super().__init__()`` be called in ``SearchStrategy`` subclasses. Subclassing ``SearchStrategy`` is not supported or part of the public API, but if you are subclassing it anyway, you will need to make sure to call ``super().__init__()`` after this release.
