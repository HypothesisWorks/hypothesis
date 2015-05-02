===================
Additional packages
===================

Hypothesis has a zero dependency policy for the core library. For things which need a
dependency to work, these are farmed off into additional packages on pypi. These end
up putting any additional things you need to import (if there are any) under the
hypothesis.extra namespace.

Generally these will be for providing new sources of data for Hypothesis, or for better
integrating it into an existing testing framework.

-------------------
hypothesis-datetime
-------------------

As might be expected, this adds support for datetime to Hypothesis.

If you install the hypothesis-datetime package then you get a strategy for datetime
out of the box:

.. code:: python

  >>> from datetime import datetime
  >>> from hypothesis import strategy

  >>> strategy(datetime).example()
  datetime.datetime(6360, 1, 3, 12, 30, 56, 185849)

  >>> strategy(datetime).example()
  datetime.datetime(6187, 6, 11, 0, 0, 23, 809965, tzinfo=<UTC>)

  >>> strategy(datetime).example()
  datetime.datetime(4076, 8, 7, 0, 15, 55, 127297, tzinfo=<DstTzInfo 'Turkey' EET+2:00:00 STD>)

So things like the following work:

.. code:: python

  @given(datetime)
  def test_365_days_are_one_year(d):
      assert (d + timedelta(days=365)).year > d.year


Or rather, the test correctly fails:

.. 

  Falsifying example: test_add_one_year(d=datetime.datetime(2000, 1, 1, 0, 0, tzinfo=<UTC>))

We forgot about leap years.

(Note: Actually most of the time you run that test it will pass because Hypothesis does not hit
January 1st on a leap year with high enough probability that it will often find it.
However the advantage of the Hypothesis database is that once this example is found
it will stay found)

We can also restrict ourselves to just naive datetimes or just timezone aware
datetimes.


.. code:: python

  from hypothesis.extra.datetime import naive_datetime, timezone_aware_datetime

  @given(naive_datetime)
  def test_naive_datetime(xs):
    assert isinstance(xs, datetime)
    assert xs.tzinfo is None

  @given(timezone_aware_datetime)
  def test_non_naive_datetime(xs):
    assert isinstance(xs, datetime)
    assert xs.tzinfo is not None


Both of the above will pass.

----------------------
hypothesis-fakefactory
----------------------

`Fake-factory <https://pypi.python.org/pypi/fake-factory>`_ is another Python
library for data generation. hypothesis-fakefactory is a package which lets you
use fake-factory generators to parametrize tests.

In hypothesis.extra.fakefactory it defines the type FakeFactory which is a
placeholder for producing data from any FakeFactory type.

So for example the following will parametrize a test by an email address:


.. code:: python

  @given(FakeFactory('email'))
  def test_email(email):
      assert '@' in email


Naturally you can compose these in all the usual ways, so e.g.

.. code:: python

  >>> from hypothesis.extra.fakefactory import FakeFactory
  >>> from hypothesis import strategy
  >>> strategy([FakeFactory('email')]).example()
  
  ['.@.com',
   '.@yahoo.com',
   'kalvelis.paulius@yahoo.com',
   'eraslan.mohsim@demirkoruturk.info']

You can also specify locales:


.. code:: python

  >>> strategy(FakeFactory('name', locale='en_US')).example()
  'Kai Grant'

  >>> strategy(FakeFactory('name', locale='fr_FR')).example()
  'Édouard Paul'

Or if you want you can specify several locales:

.. code:: python

  >>> strategy([FakeFactory('name', locales=['en_US', 'fr_FR'])]).example()
  
  ['Michel Blanchet',
   'Victor Collin',
   'Eugène Perrin',
   'Miss Bernice Satterfield MD']

If you want to your own FakeFactory providers you can do that too, passing them
in as a providers argument to the FakeFactory type. It will generally be more
powerful to use Hypothesis's custom strategies though unless you have a
specific existing provider you want to use.

-----------------
hypothesis-pytest
-----------------

hypothesis-pytest is the world's most basic pytest plugin. Install it to get
slightly better integrated example reporting when using @given and running
under pytest. That's basically all it does.

.. _hypothesis-django:

-----------------
hypothesis-django
-----------------

hypothesis-django adds support for testing your Django models with Hypothesis.
Using it is quite straightforward: All you need to do is subclass 
hypothesis.extra.django.TestCase or hypothesis.extra.django.TransactionTestCase
and you can use @given as normal, and the transactions will be per example
rather than per test function as they would be if you used @given with a normal
django test suite (this is important because your test function will be called
multiple times and you don't want them to interfere with eachother). Test cases
on these classes that do not use @given will be run as normal.

I strongly recommend not using TransactionTestCase unless you really have to.
Because Hypothesis runs this in a loop the performance problems it normally has
are significantly exacerbated and your tests will be really slow.

In addition to the above, Hypothesis has some limited support for automatically
generating instances of your models. You can use @given(MyModelClass) and this
will usually work.

The test suite integration should be pretty solid, but the automatic model
generation is highly experimental. Don't be surprised if it doesn't work very
well, but do file bug reports.

Known limitations:

1. If your model has a non-nullable field type that Hypothesis doesn't support
   then this will error with ModelNotSupported. If it has a nullable field
   type that Hypothesis doesn't support it will always be null.
2. Cycles (e.g. if A has a foreign key pointing to B and B has a foreign key
   pointing back to A) are not supported. In some limited cases a cycle where
   the foreign key is nullable will be supported but always null.
3. Children will not be populated. So if A has many B and you ask for A, you
   will get an A with no Bs referencing it.
4. Parents will not be shared, so if you ask for a list of [B] in the above,
   each of them wil have a unique A.
5. Particularly hairy constraints will sometimes cause Hypothesis to not be
   able to provide enough examples.

Basically if a model is mostly a simple data storage thing with few constraints
you should probably expect to just be able to ask Hypothesis for an instance
and have everything work. For more complicated dependencies you'll probably
want to write your own generators.

Fortunately, writing your own generators is entirely feasible! All of the
:doc:`normal data generation methods <data>` work fine with models. In
particular you should feel free to create models inside map and flatmap (or
filter if you really want to I guess). These will only ever be run inside the
transaction and anything created in them will be cleaned up as normal.
