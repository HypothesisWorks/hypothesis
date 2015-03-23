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
