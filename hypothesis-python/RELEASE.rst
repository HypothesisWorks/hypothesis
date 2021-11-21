RELEASE_TYPE: minor

Did you know that of the 2\ :superscript:`64` possible floating-point numbers,
2\ :superscript:`53` of them are ``nan`` - and Python prints them all the same way?

While nans *usually* have all zeros in the sign bit and mantissa, this
`isn't always true <https://wingolog.org/archives/2011/05/18/value-representation-in-javascript-implementations>`__,
and :wikipedia:`'signaling' nans might trap or error <https://en.wikipedia.org/wiki/NaN#Signaling_NaN>`.
To help distinguish such errors in e.g. CI logs, Hypothesis now prints ``-nan`` for
negative nans, and adds a comment like ``# Saw 3 signaling NaNs`` if applicable.
