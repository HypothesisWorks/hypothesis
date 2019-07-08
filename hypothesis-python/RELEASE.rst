RELEASE_TYPE: minor

This release deprecates ``find()``.  The ``.example()`` method is a better
replacement if you want *an* example, and for the rare occasions where you
want the *minimal* example you can get it from :func:`@given <hypothesis.given>`.

:func:`@given <hypothesis.given>` has steadily outstripped ``find()`` in both
features and performance over recent years, and as we do not have the resources
to maintain and test both we think it is better to focus on just one.
