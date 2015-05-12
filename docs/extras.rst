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

As might be expected, this provides a strategy which generates instances of
datetime. It depends on pytz.

hypothesis-datetime lives in the hypothesis.extra.datetime package:

.. code-block:: pycon

  >>> from datetime import datetime
  >>> datetimes().example()
  datetime.datetime(1705, 1, 20, 0, 32, 0, 973139, tzinfo=<DstTzInfo 'Israel...
  >>> datetimes().example()
  datetime.datetime(7274, 6, 9, 23, 0, 31, 75498, tzinfo=<DstTzInfo 'America...

As you can see, it produces years from quite a wide range. If you want to
narrow it down you can ask for a more specific range of years:

.. code-block:: pycon

  >>> datetimes(min_year=2001, max_year=2010).example()
  datetime.datetime(2010, 7, 7, 0, 15, 0, 614034, tzinfo=<DstTzInfo 'Pacif...
  >>> datetimes(min_year=2001, max_year=2010).example()
  datetime.datetime(2006, 9, 26, 22, 0, 0, 220365, tzinfo=<DstTzInfo 'Asia...

You can also specify timezones:

.. code-block:: pycon

  >>> import pytz
  >>> pytz.all_timezones[:3]
  ['Africa/Abidjan', 'Africa/Accra', 'Africa/Addis_Ababa']
  >>> datetimes(timezones=pytz.all_timezones[:3]).example()
  datetime.datetime(6257, 8, 21, 13, 6, 24, 8751, tzinfo=<DstTzInfo 'Africa/Accra' GMT0:00:00 STD>)
  >>> datetimes(timezones=pytz.all_timezones[:3]).example()
  datetime.datetime(7851, 2, 3, 0, 0, 0, 767400, tzinfo=<DstTzInfo 'Africa/Accra' GMT0:00:00 STD>)
  >>> datetimes(timezones=pytz.all_timezones[:3]).example()
  datetime.datetime(8262, 6, 22, 16, 0, 0, 154235, tzinfo=<DstTzInfo 'Africa/Abidjan' GMT0:00:00 STD>)

If the set of timezones is empty you will get a naive datetime:

.. code-block:: pycon

  >>> datetimes(timezones=[]).example()
  datetime.datetime(918, 11, 26, 2, 0, 35, 916439)

You can also explicitly get a mix of naive and non-naive datetimes if you
want:

.. code-block:: pycon

    >>> datetimes(allow_naive=True).example()
    datetime.datetime(2433, 3, 20, 0, 0, 44, 460383, tzinfo=<DstTzInfo 'Asia/Hovd' HOVT+7:00:00 STD>)
    >>> datetimes(allow_naive=True).example()
    datetime.datetime(7003, 1, 22, 0, 0, 52, 401259)

----------------------
hypothesis-fakefactory
----------------------

`Fake-factory <https://pypi.python.org/pypi/fake-factory>`_ is another Python
library for data generation. hypothesis-fakefactory is a package which lets you
use fake-factory generators to parametrize tests.

It currently only supports the 0.4.2 release of fake-factory, due to some
issues with the 0.5.0 release. These are known to be fixed in master but there
hasn't been a release containing the fixes yet.

hypothesis.extra.fakefactory defines a function fake_factory which returns a
strategy for producing text data from any FakeFactory provider.

So for example the following will parametrize a test by an email address:


.. code-block:: pycon

    >>> fake_factory('email').example()
    'tnader@prosacco.info'

    >>> fake_factory('name').example()
    'Zbyněk Černý CSc.'

You can explicitly specify the locale (otherwise it uses any of the available
locales), either as a single locale or as several:

.. code-block:: pycon

    >>> fake_factory('name', locale='en_GB').example()
    'Antione Gerlach'
    >>> fake_factory('name', locales=['en_GB', 'cs_CZ']).example()
    'Miloš Šťastný'
    >>> fake_factory('name', locales=['en_GB', 'cs_CZ']).example()
    'Harm Sanford'

If you want to your own FakeFactory providers you can do that too, passing them
in as a providers argument:

.. code-block:: pycon

    >>> from faker.providers import BaseProvider
    >>> class KittenProvider(BaseProvider):
    ...     def meows(self):
    ...             return 'meow %d' % (self.random_number(digits=10),)
    ... 
    >>> fake_factory('meows', providers=[KittenProvider]).example()
    'meow 9139348419'

Generally you probably shouldn't do this unless you're reusing a provider you
already have - Hypothesis's facilities for strategy generation are much more
powerful and easier to use. Consider using something like BasicStrategy instead
if you want to write a strategy from scratch. This is only here to provide easy
reuse of things you already have.

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
deriving strategies for your model types, which you can then customize further.

Warning: Hypothesis creates saved models. This will run inside your testing
transaction when using the test runner, but if you use the dev console this
will leave debris in your database.

For example, using the trivial django project I have for testing:

.. code-block:: pycon

    >>> from hypothesis.extra.django.models import models
    >>> from toystore.models import Customer
    >>> c = models(Customer).example()
    >>> c
    <Customer: Customer object>
    >>> c.email
    'jaime.urbina@gmail.com'
    >>> c.name
    '\U00109d3d\U000e07be\U000165f8\U0003fabf\U000c12cd\U000f1910\U00059f12\U000519b0\U0003fabf\U000f1910\U000423fb\U000423fb\U00059f12\U000e07be\U000c12cd\U000e07be\U000519b0\U000165f8\U0003fabf\U0007bc31'
    >>> c.age
    -873375803

Hypothesis has just created this with whatever the relevant type of data is.

Obviously the customer's age is implausible, so lets fix that:

.. code-block:: pycon

    >>> from hypothesis.strategies import integers
    >>> c = models(Customer, age=integers(min_value=0, max_value=120)).example()
    >>> c
    <Customer: Customer object>
    >>> c.age
    5

You can use this to override any fields you like. Sometimes this will be
mandatory: If you have a non-nullable field of a type Hypothesis doesn't know
how to create (e.g. a foreign key) then the models function will error unless
you explicitly pass a strategy to use there.

You can also register a default strategy for a field type if you have custom
one that Hypothesis doesn't know about or want to override the normal behaviour
for some reason:

.. code-block:: pycon

    >>> from toystore.models import CustomishField, Customish
    >>> models(Customish).example()
    hypothesis.errors.InvalidArgument: Missing arguments for mandatory field
        customish for model Customish
    >>> from hypothesis.extra.django.models import add_default_field_mapping
    >>> from hypothesis.strategies import just
    >>> add_default_field_mapping(CustomishField, just("hi"))
    >>> x = models(Customish).example()
    >>> x.customish
    'hi'

Note that this mapping is on exact type. Subtypes will not inherit it.
