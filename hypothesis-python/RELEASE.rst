RELEASE_TYPE: patch

This release further improves printing of generated values, building on the changes
in  :version:`6.151.11`.

Principle changes:

* In many cases where we would have printed a complex expression
  producing a value, we now print the repr (or a pretty-printed version of it).
* Additionally, in some cases where we would print a complex expression that involved
  a lambda, we are now able to simplify that expression into a more readable one.
