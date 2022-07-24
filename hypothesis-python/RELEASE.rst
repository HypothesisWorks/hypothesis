RELEASE_TYPE: patch

This patch fixes ``hypothesis.extra.pytz`` with the latest version of the
:pypi:`types-pytz` package.

Note that we recommend using the standard-library :mod:`zoneinfo` module
(or :pypi:`backports.zoneinfo` before Python 3.9) or :pypi:`dateutil`
package, `because pytz is not really compatible with Python datetimes
<https://blog.ganssle.io/articles/2018/03/pytz-fastest-footgun.html>`__.
