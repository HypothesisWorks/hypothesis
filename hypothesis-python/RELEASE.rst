RELEASE_TYPE: patch

This patch improves the speed of the explain phase on python 3.12+, by using the new
:mod:`sys.monitoring` module to collect coverage, instead of :obj:`sys.settrace`.

Thanks to Liam DeVoe for :pull:`3776`!
