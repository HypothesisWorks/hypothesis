RELEASE_TYPE: patch

This patch implements filter-rewriting for most length filters on some
additional collection types (:issue:`3795`), and fixes several latent
bugs where unsatisfiable or partially-infeasible rewrites could trigger
internal errors.
