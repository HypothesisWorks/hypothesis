|@given|
========

.. autofunction:: hypothesis.given

.. data:: hypothesis.infer

Arguments to |@given|
---------------------

The |@given| decorator may be used to specify which arguments of a function should be parametrized over. You can use either positional or keyword arguments, but not a mixture of both.

For example, all of the following are valid uses:

.. code:: python

  @given(integers(), integers())
  def a(x, y):
      pass


  @given(integers())
  def b(x, y):
      pass


  @given(y=integers())
  def c(x, y):
      pass


  @given(x=integers())
  def d(x, y):
      pass


  @given(x=integers(), y=integers())
  def e(x, **kwargs):
      pass


  @given(x=integers(), y=integers())
  def f(x, *args, **kwargs):
      pass


  class SomeTest(TestCase):
      @given(integers())
      def test_a_thing(self, x):
          pass

The following are not:

.. code:: python

  @given(integers(), integers(), integers())
  def g(x, y):
      pass


  @given(integers())
  def h(x, *args):
      pass


  @given(integers(), x=integers())
  def i(x, y):
      pass


  @given()
  def j(x, y):
      pass


The rules for determining what are valid uses of ``given`` are as follows:

1. You may pass any keyword argument to ``given``.
2. Positional arguments to ``given`` are equivalent to the rightmost named arguments for the test function.
3. Positional arguments may not be used if the underlying test function has ``*args``, ``**kwargs``, or keyword-only arguments.
4. Functions tested with ``given`` may not have any defaults.

The reason for the "rightmost named arguments" behaviour is so that using |@given| with instance methods works: ``self`` will be passed to the function as normal and not be parametrized over.

The function returned by given has all the same arguments as the original test, minus those that are filled in by |@given|. Check :ref:`the notes on framework compatibility <framework-compatibility>` to see how this affects other testing libraries you may be using.

Inferred strategies
-------------------

In some cases, Hypothesis can work out what to do when you omit arguments. This is based on introspection, *not* magic, and therefore has well-defined limits.

|st.builds| will check the signature of the ``target`` (using :func:`python:inspect.signature`). If there are required arguments with type annotations and
no strategy was passed to |st.builds|, |st.from_type| is used to fill them in. You can also pass the value ``...`` (``Ellipsis``) as a keyword argument, to force this inference for arguments with a default value.

.. code-block:: pycon

    >>> def func(a: int, b: str):
    ...     return [a, b]
    ...
    >>> builds(func).example()
    [-6993, '']

|@given| does not perform any implicit inference for required arguments, as this would break compatibility with pytest fixtures. ``...`` (:obj:`python:Ellipsis`), can be used as a keyword argument to explicitly fill in an argument from its type annotation.  You can also use the :obj:`hypothesis.infer` alias if writing a literal ``...`` seems too weird.

.. code:: python

    @given(a=...)  # or @given(a=infer)
    def test(a: int):
        pass


    # is equivalent to
    @given(a=from_type(int))
    def test(a):
        pass


``@given(...)`` can also be specified to fill all arguments from their type annotations.

.. code:: python

    @given(...)
    def test(a: int, b: str):
        pass


    # is equivalent to
    @given(a=..., b=...)
    def test(a, b):
        pass


Limitations
~~~~~~~~~~~

Hypothesis does not inspect :pep:`484` type comments at runtime. While |st.from_type| will work as usual, inference in |st.builds| and |@given| will only work if you manually create the ``__annotations__`` attribute (e.g. by using ``@annotations(...)`` and ``@returns(...)`` decorators).

The :mod:`python:typing` module changes between different Python releases, including at minor versions.  These are all supported on a best-effort basis, but you may encounter problems.  Please report them to us, and consider updating to a newer version of Python as a workaround.
