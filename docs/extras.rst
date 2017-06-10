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
hypothesis[pytz]
--------------------

.. automodule:: hypothesis.extra.pytz
   :members:


--------------------
hypothesis[datetime]
--------------------

.. automodule:: hypothesis.extra.datetime
   :members:


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
powerful and easier to use. This is only here to provide easy
reuse of things you already have.

------------------
hypothesis[django]
------------------

hypothesis.extra.django adds support for testing your Django models with Hypothesis.

It is tested extensively against all versions of Django in mainstream or
extended support, including LTS releases.  It *may* be compatible with
earlier versions too, but there's no support from us either and you really
should update to get security patches.

It's large enough that it is :doc:`documented elsewhere <django>`.

------------------
hypothesis[numpy]
------------------

hypothesis.extra.numpy adds support for testing your Numpy code with Hypothesis.

This includes generating arrays, array shapes, and both scalar or compound dtypes.

Like the Django extra, :doc:`Numpy has it's own page <numpy>`.
