RELEASE_TYPE: patch

Numpy array strategy returned dtype is always unkown but it's actually specified
as parameter. 

This patch made that relationship between dtype parameters and returned strategy
dtype explicit.
