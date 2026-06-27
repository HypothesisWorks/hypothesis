RELEASE_TYPE: patch

This patch fixes a bug where an exception raised by a test after its data had
already been frozen - for example in a teardown step, or after an explicit
freeze - was silently swallowed instead of propagating to the user
(:issue:`4132`).
