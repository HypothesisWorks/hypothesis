RELEASE_TYPE: minor

This module includes support for strategies which generate arguments to
functions that follow the numpy general universal function API. So, it can
automatically generate the matrices with shapes that follow the shape
constraints. For example, to generate test inputs for `np.dot`, one can use,
``@gufunc_args('(m,n),(n,p)->(m,p)', dtype=np.float_, elements=floats())``
We also allow for adding extra dimensions that follow the numpy broadcasting
conventions via
``@gufunc_args('(m,n),(n,p)->(m,p)', dtype=np.float_, elements=floats(), max_dims_extra=3)``
This can be used when checking if a function follows the correct numpy
broadcasting semantics.
