RELEASE_TYPE: patch

One of our shrinking passes for reducing failing inputs targets failures which require two numbers to add to the same value. This pass previously only worked for positive numbers. This patch fixes that, so it also works for negative numbers.
