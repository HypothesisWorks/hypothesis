RELEASE_TYPE: minor

:func:`~hypothesis.extra.django.from_field` now supports
:class:`~django.contrib.auth.forms.UsernameField` and
:class:`~django.contrib.auth.forms.ReadOnlyPasswordHashField`
from ``django.contrib.auth.forms``.

Thanks to Afonso Silva for reporting and fixing :issue:`3417`.