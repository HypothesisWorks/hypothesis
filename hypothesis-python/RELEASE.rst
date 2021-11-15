RELEASE_TYPE: patch

This patch fixes a rare internal error in the :func:`hypothesis.strategies.datetimes`
strategy, where the implementation of ``allow_imaginary=False`` crashed when checking
a time during the skipped hour of a DST transition *if* the DST offset is negative -
only true of ``Europe/Dublin``, who we presume have their reasons - and the ``tzinfo``
object is a :pypi:`pytz` timezone (which predates :pep:`495`).
