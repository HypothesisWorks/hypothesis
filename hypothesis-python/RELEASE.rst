RELEASE_TYPE: minor

This release adds :PEP:`484` type hints to Hypothesis on a provisional
basis, using the comment-based syntax for Python 2 compatibility.  You
can :ref:`read more about our type hints here <our-type-hints>`.

It *also* adds the ``py.typed`` marker specified in :PEP:`561`.
After you ``pip install hypothesis``, :pypi:`mypy` 0.590 or later
will therefore type-check your use of our public interface!
