This module includes support for strategies which generate arguments to
functions that follow the numpy general universal function API. So, it can
automatically generate the matrices with shapes that follow the shape
constraints. For example, to generate test inputs for `np.dot`, one can use,
```
@gufunc('(m,n),(n,p)->(m,p)', dtype=np.float_, elements=floats())
```
We also allow for adding extra dimensions that follow the numpy broadcasting
conventions via
```
@gufunc_broadcast('(m,n),(n,p)->(m,p)', dtype=np.float_, elements=floats())
```
The convenience strategies `broadcasted` and `axised` make it easy to check if
your numpy function follows the correct broadcasting conventions as defined by
`np.vectorize` and `np.apply_along_axis`.
