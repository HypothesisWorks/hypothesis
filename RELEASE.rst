RELEASE_TYPE: patch

This release fixes a bug with generating numpy datetime and timedelta types:
When inferring the strategy from the dtype, datetime and timedelta dtypes with
sub-second precision would always produce examples with one second resolution.
Inferring a strategy from a time dtype will now always produce example with the
same precision.
