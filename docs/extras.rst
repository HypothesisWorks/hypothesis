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

There are seperate pages for :doc:`django` and :doc:`numpy`.

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


.. _faker-extra:

-----------------------
hypothesis[fakefactory]
-----------------------

.. note::
    This extra package is deprecated.  We strongly recommend using native
    Hypothesis strategies, which are more effective at both finding and
    shrinking failing examples for your tests.

    The :func:`~hypothesis.strategies.from_regex`,
    :func:`~hypothesis.strategies.text` (with some specific alphabet), and
    :func:`~hypothesis.strategies.sampled_from` strategies may be particularly
    useful.

:pypi:`Faker` (previously :pypi:`fake-factory`) is a Python package that
generates fake data for you. It's great for bootstraping your database,
creating good-looking XML documents, stress-testing a database, or anonymizing
production data.  However, it's not designed for automated testing - data from
Hypothesis looks less realistic, but produces minimal bug-triggering examples
and uses coverage information to check more cases.

``hypothesis.extra.fakefactory`` lets you use Faker generators to parametrize
Hypothesis tests.  This was only ever meant to ease your transition to
Hypothesis, but we've improved Hypothesis enough since then that we no longer
recommend using Faker for automated tests under any circumstances.

hypothesis.extra.fakefactory defines a function fake_factory which returns a
strategy for producing text data from any Faker provider.

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

You can use custom Faker providers via the ``providers`` argument:

.. code-block:: pycon

    >>> from faker.providers import BaseProvider
    >>> class KittenProvider(BaseProvider):
    ...     def meows(self):
    ...         return 'meow %d' % (self.random_number(digits=10),)
    >>> fake_factory('meows', providers=[KittenProvider]).example()
    'meow 9139348419'
