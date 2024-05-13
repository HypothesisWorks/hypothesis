RELEASE_TYPE: minor

The :func:`~hypothesis.extra.django.from_model` function currently
tries to create a strategy for :obj:`~django:django.db.models.AutoField`
fields if they don't have :attr:`~django:django.db.models.Field.auto_created`
set to `True`.  The docs say it's supposed to skip all
:obj:`~django:django.db.models.AutoField` fields, so this patch updates
the code to do what the docs say (:issue:`3978`).
