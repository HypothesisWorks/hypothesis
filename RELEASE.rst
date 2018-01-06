RELEASE_TYPE: patch

This patch blacklists null characters (``'\x00'``) in automatically created
strategies for Django :obj:`~django:django.db.models.CharField` and
:obj:`~django:django.db.models.TextField`, due to a database issue which
`was recently fixed upstream <https://code.djangoproject.com/ticket/28201>`_
(Hypothesis :issue:`1045`).
