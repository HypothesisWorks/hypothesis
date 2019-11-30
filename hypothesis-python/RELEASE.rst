RELEASE_TYPE: patch

This patch fixes :issue:`2229`, where Numpy arrays of unsized strings would
only ever have strings of size one due to an interaction between our generation
logic and Numpy's allocation strategy.
