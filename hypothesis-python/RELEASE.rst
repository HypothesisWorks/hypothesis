RELEASE_TYPE: patch

This release reverts the changes to logging handling in 3.69.11,
which broke test that use the :pypi:`pytest` ``caplog`` fixture
internally because all logging was disabled (:issue:`1546`).
