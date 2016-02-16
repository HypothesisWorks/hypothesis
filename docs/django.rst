.. _hypothesis-django:

===========================
Hypothesis for Django users
===========================

Hypothesis offers a number of features specific for Django testing, available
in the :mod:`hypothesis[django]` :doc:`extra </extras>`.

Using it is quite straightforward: All you need to do is subclass
:class:`hypothesis.extra.django.TestCase` or
:class:`hypothesis.extra.django.TransactionTestCase`
and you can use :func:`@given <hypothesis.core.given>` as normal,
and the transactions will be per example
rather than per test function as they would be if you used @given with a normal
django test suite (this is important because your test function will be called
multiple times and you don't want them to interfere with eachother). Test cases
on these classes that do not use
:func:`@given <hypothesis.core.given>` will be run as normal.

I strongly recommend not using
:class:`~hypothesis.extra.django.TransactionTestCase`
unless you really have to.
Because Hypothesis runs this in a loop the performance problems it normally has
are significantly exacerbated and your tests will be really slow.

In addition to the above, Hypothesis has some limited support for automatically
deriving strategies for your model types, which you can then customize further.

.. warning::
    Hypothesis creates saved models. This will run inside your testing
    transaction when using the test runner, but if you use the dev console this
    will leave debris in your database.

For example, using the trivial django project I have for testing:

.. code-block:: python

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

.. code-block:: python

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

Foreign keys are not automatically derived. If they're nullable they will default
to always being null, otherwise you always have to specify them. e.g. suppose
we had a Shop type with a foreign key to company, we would define a strategy
for it as:

.. code:: python

  shop_strategy = models(Shop, company=models(Company))


--------
Fixtures
--------

The other way you can use Hypothesis for testing your Django project is to
replace your fixtures. This feature is a bit new and experimental but seems
to work pretty well.

Hypothesis offers a function *fixture* which lets you specify a single example
to use in your tests by what properties it should satisfy. For example, suppose
we want a Company with a long name (I have no idea why) you could specify:


.. code:: python

  from hypothesis.extra.django.models import models
  from hypothesis.extra.django.fixtures import fixture

  from toystore.models import Company

  a_company = fixture(
      models(Company),
      lambda c: len(c.name) >= 10,
  )

This gives you a function that you can call from within your tests to get a
value of the desired type matching these conditions:

.. code:: python

  from hypothesis.extra.django.models import models
  from hypothesis.extra.django.fixtures import fixture

  from toystore.models import Company

  class TestCompany(TestCase):
      def test_can_find_unique_name(self):
          assert len(a_company().name) >= 10

Unlike normal tests with Hypothesis this doesn't randomize your test, and you
only run it once: Hypothesis has built and minimized an example before the test
ever runs, then it just provides you with that example each time. This lacks
much of the power of normal Hypothesis, but may be a lot more convenient to use
in some cases and lets you still get many of the benefits of using its data
generation while writing a more classic style of test. It's also a lot less
annoying than writing your fixtures by hand.

Each time you call a single fixture in your test will give you the same
example back, so e.g. the following test will pass:

.. code:: python

    def test_two_calls_to_fixture_are_the_same(self):
        assert a_company().pk == a_company().pk

You can also use multiple fixtures in the same test. These will always give
different results, even if their definitions are the same:

.. code:: python

  from hypothesis.extra.django.models import models
  from hypothesis.extra.django.fixtures import fixture

  from toystore.models import Company

  company1 = fixture(models(Company))
  company2 = fixture(models(Company))

  class TestCompany(TestCase):
      def test_two_fixtures(self):
          assert company1().pk != company2().pk

Note that fixtures don't have to define models. They can define any type you
like. e.g. the following gives us a list containing at least 3 distinct companies:


.. code:: python

  some_companies = fixture(
    models(Company), lambda cs: len({c.pk for c in cs}) >= 3
  )

(Note we ask for three distinct primary keys rather than just the length of
the company: Otherwise we'd probably have got the same company 3 times)

Some caveats:

1. If you have unique constraints then you should call fixture functions
   before instantiating any models yourself, or you may get integrity errors
   when Hypothesis tries to create the fixture.
2. Fixtures can make startup quite slow the first time as Hypothesis has to work
   out the example to use. Values are cached in the Hypothesis example
   database (which has nothing to do with your Django test database), stored
   by default in .hypothesis/examples.db. You might wish to cache this
   between test runs on your CI server, as it will significantly improve startup
   performance.
3. Hypothesis creates and destroys test databases during fixture definition.
   This is normal and you shouldn't be concerned if you notice it. It would be
   nice if this weren't necessary and if anyone has a better idea about how to
   do it, please talk to me...

---------------
Tips and tricks
---------------

Custom field types
==================

If you have a custom Django field type you can register it with Hypothesis's
model deriving functionality by registering a default strategy for it:

.. code-block:: python

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


Generating child models
=======================

For the moment there's no explicit support in hypothesis-django for generating
dependent models. i.e. a Company model will generate no Shops. However if you
want to generate some dependent models as well, you can emulate this by using
the *flatmap* function as follows:

.. code:: python

  from hypothesis.strategies import lists, just

  def generate_with_shops(company):
    return lists(models(Shop, company=just(company))).map(lambda _: company)

  company_with_shops_strategy = models(Company).flatmap(generate_with_shops)

Lets unpack what this is doing:

The way flatmap works is that we draw a value from the original strategy, then
apply a function to it which gives us a new strategy. We then draw a value from
*that* strategy. So in this case we're first drawing a company, and then we're
drawing a list of shops belonging to that company: The *just* strategy is a
strategy such that drawing it always produces the individual value, so
``models(Shop, company=just(company))`` is a strategy that generates a Shop belonging
to the original company.

So the following code would give us a list of shops all belonging to the same
company:

.. code:: python

  models(Company).flatmap(lambda c: lists(models(Shop, company=just(c))))

The only difference from this and the above is that we want the company, not
the shops. This is where the inner map comes in. We build the list of shops
and then throw it away, instead returning the company we started for. This
works because the models that Hypothesis generates are saved in the database,
so we're essentially running the inner strategy purely for the side effect of
creating those children in the database.
