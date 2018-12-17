RELEASE_TYPE: patch

This patch fixes :issue:`1700`, where a line that contained a Unicode character
before a lambda definition would cause an internal exception.