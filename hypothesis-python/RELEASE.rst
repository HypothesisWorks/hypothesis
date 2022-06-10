RELEASE_TYPE: patch

Our pretty-printer no longer sorts dictionary keys, since iteration order is
stable in Python 3.7+ and this can affect reproducing examples (:issue:`3370`).
This PR was kindly supported by `Ordina Pythoneers
<https://www.ordina.nl/vakgebieden/python/>`__.
