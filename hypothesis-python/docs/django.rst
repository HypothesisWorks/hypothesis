.. _hypothesis-django:

=====================
Hypothesis for Django
=====================

Hypothesis offers a number of features specific for Django testing, available
in the ``hypothesis[django]`` :doc:`extra </extras>`.  This is tested
against each supported series with mainstream or extended support -
if you're still getting security patches, you can test with Hypothesis.

.. class:: hypothesis.extra.django.TestCase

Using it is quite straightforward: All you need to do is subclass
:class:`hypothesis.extra.django.TestCase` or
:class:`hypothesis.extra.django.TransactionTestCase` or
:class:`~hypothesis.extra.django.LiveServerTestCase` or
:class:`~hypothesis.extra.django.StaticLiveServerTestCase`
and you can use :func:`@given <hypothesis.given>` as normal,
and the transactions will be per example
rather than per test function as they would be if you used :func:`@given <hypothesis.given>` with a normal
django test suite (this is important because your test function will be called
multiple times and you don't want them to interfere with each other). Test cases
on these classes that do not use
:func:`@given <hypothesis.given>` will be run as normal.

.. class:: hypothesis.extra.django.TransactionTestCase
.. class:: hypothesis.extra.django.LiveServerTestCase
.. class:: hypothesis.extra.django.StaticLiveServerTestCase

We recommend avoiding :class:`~hypothesis.extra.django.TransactionTestCase`
unless you really have to run each test case in a database transaction.
Because Hypothesis runs this in a loop, the performance problems it normally has
are significantly exacerbated and your tests will be really slow.
If you are using :class:`~hypothesis.extra.django.TransactionTestCase`,
you may need to use ``@settings(suppress_health_check=[HealthCheck.too_slow])``
to avoid :ref:`errors due to slow example generation <healthchecks>`.

Having set up a test class, you can now pass :func:`@given <hypothesis.given>`
a strategy for Django models:

.. autofunction:: hypothesis.extra.django.from_model

For example, using :gh-file:`the trivial django project we have for testing
<hypothesis-python/tests/django/toystore/models.py>`:

.. code-block:: pycon

    >>> from hypothesis.extra.django import from_model
    >>> from toystore.models import Customer
    >>> c = from_model(Customer).example()
    >>> c
    <Customer: Customer object>
    >>> c.email
    'jaime.urbina@gmail.com'
    >>> c.name
    '\U00109d3d\U000e07be\U000165f8\U0003fabf\U000c12cd\U000f1910\U00059f12\U000519b0\U0003fabf\U000f1910\U000423fb\U000423fb\U00059f12\U000e07be\U000c12cd\U000e07be\U000519b0\U000165f8\U0003fabf\U0007bc31'
    >>> c.age
    -873375803

Hypothesis has just created this with whatever the relevant type of data is.

Obviously the customer's age is implausible, which is only possible because
we have not used (eg) :class:`~django:django.core.validators.MinValueValidator`
to set the valid range for this field (or used a
:class:`~django:django.db.models.PositiveSmallIntegerField`, which would only
need a maximum value validator).

If you *do* have validators attached, Hypothesis will only generate examples
that pass validation.  Sometimes that will mean that we fail a
:class:`~hypothesis.HealthCheck` because of the filtering, so let's explicitly
pass a strategy to skip validation at the strategy level:

.. code-block:: pycon

    >>> from hypothesis.strategies import integers
    >>> c = from_model(Customer, age=integers(min_value=0, max_value=120)).example()
    >>> c
    <Customer: Customer object>
    >>> c.age
    5

.. autofunction:: hypothesis.extra.django.from_form

---------------
Tips and tricks
---------------

Custom field types
==================

If you have a custom Django field type you can register it with Hypothesis's
model deriving functionality by registering a default strategy for it:

.. code-block:: pycon

    >>> from toystore.models import CustomishField, Customish
    >>> from_model(Customish).example()
    hypothesis.errors.InvalidArgument: Missing arguments for mandatory field
        customish for model Customish
    >>> from hypothesis.extra.django import register_field_strategy
    >>> from hypothesis.strategies import just
    >>> register_field_strategy(CustomishField, just("hi"))
    >>> x = from_model(Customish).example()
    >>> x.customish
    'hi'

Note that this mapping is on exact type. Subtypes will not inherit it.

.. autofunction:: hypothesis.extra.django.register_field_strategy

.. autofunction:: hypothesis.extra.django.from_field


Generating child models
=======================

For the moment there's no explicit support in hypothesis-django for generating
dependent models. i.e. a Company model will generate no Shops. However if you
want to generate some dependent models as well, you can emulate this by using
the *flatmap* function as follows:

.. code:: python

  from hypothesis.strategies import just, lists


  def generate_with_shops(company):
      return lists(from_model(Shop, company=just(company))).map(lambda _: company)


  company_with_shops_strategy = from_model(Company).flatmap(generate_with_shops)

Let's unpack what this is doing:

The way flatmap works is that we draw a value from the original strategy, then
apply a function to it which gives us a new strategy. We then draw a value from
*that* strategy. So in this case we're first drawing a company, and then we're
drawing a list of shops belonging to that company: The *just* strategy is a
strategy such that drawing it always produces the individual value, so
``from_model(Shop, company=just(company))`` is a strategy that generates a Shop belonging
to the original company.

So the following code would give us a list of shops all belonging to the same
company:

.. code:: python

  from_model(Company).flatmap(lambda c: lists(from_model(Shop, company=just(c))))

The only difference from this and the above is that we want the company, not
the shops. This is where the inner map comes in. We build the list of shops
and then throw it away, instead returning the company we started for. This
works because the models that Hypothesis generates are saved in the database,
so we're essentially running the inner strategy purely for the side effect of
creating those children in the database.


.. _django-generating-primary-key:

Generating primary key values
=============================

If your model includes a custom primary key that you want to generate
using a strategy (rather than a default auto-increment primary key)
then Hypothesis has to deal with the possibility of a duplicate
primary key.

If a model strategy generates a value for the primary key field,
Hypothesis will create the model instance with
:meth:`~django:django.db.models.query.QuerySet.update_or_create`,
overwriting any existing instance in the database for this test case
with the same primary key.


On the subject of ``MultiValueField``
=====================================

Django forms feature the :class:`~django:django.forms.MultiValueField`
which allows for several fields to be combined under a single named field, the
default example of this is the :class:`~django:django.forms.SplitDateTimeField`.

.. code:: python

  class CustomerForm(forms.Form):
      name = forms.CharField()
      birth_date_time = forms.SplitDateTimeField()

``from_form`` supports ``MultiValueField`` subclasses directly, however if you
want to define your own strategy be forewarned that Django binds data for a
``MultiValueField`` in a peculiar way. Specifically each sub-field is expected
to have its own entry in ``data`` addressed by the field name
(e.g. ``birth_date_time``) and the index of the sub-field within the
``MultiValueField``, so form ``data`` for the example above might look
like this:

.. code:: python

  {
      "name": "Samuel John",
      "birth_date_time_0": "2018-05-19",  # the date, as the first sub-field
      "birth_date_time_1": "15:18:00",  # the time, as the second sub-field
  }

Thus, if you want to define your own strategies for such a field you must
address your sub-fields appropriately:

.. code:: python

  from_form(CustomerForm, birth_date_time_0=just("2018-05-19"))
