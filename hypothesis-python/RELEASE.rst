RELEASE_TYPE: patch

:ref:`fuzz_one_input <fuzz_one_input>` is now implemented using an :ref:`alternative backend <alternative-backends>`. This brings the interpretation of the fuzzer-provided bytestring closer to the fuzzer mutations, allowing the mutations to work more reliably. We hope to use this backend functionality to improve fuzzing integration (see e.g. https://github.com/google/atheris/issues/20) in the future!
