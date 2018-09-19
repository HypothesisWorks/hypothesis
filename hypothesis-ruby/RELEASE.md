RELEASE_TYPE: patch
This release makes the code useable via a direct require.
I.e. no need for rubygems or any special LOAD_PATH.

For example, if the base directory were in /opt, you'd just say:
require "/opt/hypothesis/hypothesis-ruby/lib/hypothesis"
