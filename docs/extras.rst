===================
Additional packages
===================

Hypothesis itself does not have any dependencies, but there are some packages that
need additional things installed in order to work.

You can install these dependencies using the setuptools extra feature as e.g.
pip install hypothesis[django]. This will check installation of compatible versions.

You can also just install hypothesis into a project using them, ignore the version
constraints, and hope for the best.

In general "Which version is Hypothesis compatible with?" is a hard question to answer
and even harder to regularly test. Hypothesis is always tested against the latest
compatible version and each package will note the expected compatibility range. If
you run into a bug with any of these please specify the dependency version.

--------------------
hypothesis[datetime]
--------------------

As might be expected, this provides a strategy which generates instances of
datetime. It depends on pytz to work.

It should work with just about any version of pytz. pytz has a very stable API
and Hypothesis works around a bug or two in older versions.

It lives in the hypothesis.extra.datetime package:

.. code-block:: pycon

  >>> from hypothesis.extra.datetime import datetimes
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

-----------------------
hypothesis[fakefactory]
-----------------------

`Fake-factory <https://pypi.python.org/pypi/fake-factory>`_ is another Python
library for data generation. hypothesis.extra.fakefactory is a package which
lets you use fake-factory generators to parametrize tests.

The fake-factory API is extremely unstable, even between patch releases, and
Hypothesis's support for it is unlikely to work with anything except the exact
version it has been tested against.

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

------------------
hypothesis[django]
------------------

hypothesis.extra.django adds support for testing your Django models with Hypothesis.

It should be compatible with any Django since 1.7, but is only tested extensively
against 1.8.

It's large enough that it is :doc:`documented elsewhere <django>`.

-----------------
hypothesis-pytest
-----------------

hypothesis-pytest is actually available as a separate package that is installed as
hypothesis-pytest rather than hypothesis[pytest]. This may change in future but the
package will remain for compatibility reasons if it does.

hypothesis-pytest is the world's most basic pytest plugin. Install it to get
slightly better integrated example reporting when using @given and running
under pytest. That's basically all it does.

