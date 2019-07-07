RELEASE_TYPE: patch

This patch ensures that the Pandas extra will keep working when Python 3.8
removes abstract base classes from the top-level :obj:`python:collections`
namespace.  This also fixes the relevant warning in Python 3.7, but there
is no other difference in behaviour and you do not need to do anything.
