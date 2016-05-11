===================
Additional packages
===================

Hypothesis itself does not have any dependencies, but there are some packages that
need additional things installed in order to work.

You can install these dependencies using the setuptools extra feature as e.g.
``pip install hypothesis[django]``. This will check installation of compatible versions.

You can also just install hypothesis into a project using them, ignore the version
constraints, and hope for the best.

In general "Which version is Hypothesis compatible with?" is a hard question to answer
and even harder to regularly test. Hypothesis is always tested against the latest
compatible version and each package will note the expected compatibility range. If
you run into a bug with any of these please specify the dependency version.

--------------------
hypothesis[datetime]
--------------------

As might be expected, this provides strategies for which generating instances
of objects from the ``datetime`` module: ``datetime``\s, ``date``\s, and
``time``\s. It depends on ``pytz`` to work.

It should work with just about any version of ``pytz``. ``pytz`` has a very
stable API and Hypothesis works around a bug or two in older versions.

It lives in the ``hypothesis.extra.datetime`` package.


.. method:: datetimes(allow_naive=None, timezones=None, min_year=None, \
                      max_year=None)

    This strategy generates ``datetime`` objects. For example:

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


.. method:: dates(min_year=None, max_year=None)

    This strategy generates ``date`` objects. For example:

    .. code-block:: pycon

        >>> from hypothesis.extra.datetime import dates
        >>> dates().example()
        datetime.date(1687, 3, 23)
        >>> dates().example()
        datetime.date(9565, 5, 2)

    Again, you can restrict the range with the ``min_year`` and ``max_year``
    arguments.


.. method:: times(allow_naive=None, timezones=None)

    This strategy generates ``time`` objects. For example:

    .. code-block:: pycon

        >>> from hypothesis.extra.datetime import times
        >>> times().example()
        datetime.time(0, 15, 55, 188712, tzinfo=<DstTzInfo 'US/Hawaii' LMT-1 day, 13:29:00 STD>)
        >>> times().example()
        datetime.time(9, 0, 47, 959374, tzinfo=<DstTzInfo 'Pacific/Bougainville' BST+11:00:00 STD>)

    The ``allow_naive`` and ``timezones`` arguments act the same as the datetimes strategy.


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

------------------
hypothesis[numpy]
------------------

hypothesis.extra.numpy adds support for testing 
`NumPy <http://www.numpy.org/>`_-based implementations with Hypothesis by 
providing an ``arrays`` function.

It lives in the ``hypothesis.extra.numpy`` package.

.. method:: arrays(dtype, shape, elements=None)

    Arrays of specified `dtype` and `shape` are generated for example 
    like this:

    .. code-block:: pycon

      >>> import numpy as np
      >>> arrays(np.int8, (2, 3)).example()
      array([[-8,  6,  3],
             [-6,  4,  6]], dtype=int8)


    However, to obtain more fine grained control over the elements, use
    the `elements` keyword (see also :doc:`What you can generate and how <data>`):

    .. code-block:: pycon

      >>> import numpy as np
      >>> from hypothesis.strategies import floats
      >>> arrays(np.float, 3, elements=floats(min_value=0, max_value=1)).example()
      array([ 0.88974794,  0.77387938,  0.1977879 ])

    By combining different strategies, the shape of the array can be modified as well:

    .. code-block:: pycon

      >>> import numpy as np
      >>> from hypothesis.strategies import integers, floats
      >>>
      >>> def rnd_len_arrays(dtype, min_len=0, max_len=3, elements=None):
      ...     lengths = integers(min_value=min_len, max_value=max_len)
      ...     return lengths.flatmap(lambda n: arrays(dtype, n, elements=elements))
      ... 
      >>> 
      >>> rla = rnd_len_arrays(np.int8)
      >>> rla.example()
      array([], dtype=int8)
      >>> rla.example()
      array([-2], dtype=int8)
      >>> rla.example()
      array([ 7, -6, -2], dtype=int8)
