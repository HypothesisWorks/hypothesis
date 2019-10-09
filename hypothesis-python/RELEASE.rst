RELEASE_TYPE: minor

This release fixes a bug where our example database logic did not distinguish 
between failing examples based on arguments from a ``@pytest.mark.parametrize(...)``.
This could in theory cause data loss if a common failure overwrote a rare one, and
in practice caused occasional file-access collisions in highly concurrent workloads
(e.g. during a 300-way parametrize on 16 cores).

For internal reasons this also involves bumping the minimum supported version of
:pypi:`pytest` to 4.3

Thanks to Peter C Kroon for the Hacktoberfest patch!