from hypothesis.verifier import Verifier, Unfalsifiable, UnsatisfiedAssumption

def given(*generator_arguments,**kwargs):
    if "verifier" in kwargs:
        verifier = kwargs["verifier"]
        del kwargs["verifier"]
    else:
        verifier = Verifier()

    def run_test_with_generator(test):
        def wrapped_test(*arguments):
            # The only thing we accept in falsifying the test are exceptions 
            # Returning successfully is always a pass.
            def to_falsify(xs):
                testargs, testkwargs = xs
                try:
                    test(*(arguments + testargs), **testkwargs) 
                    return True
                except UnsatisfiedAssumption as e:
                    raise e
                except Exception:
                    return False

            try:
                falsifying_example = verifier.falsify(to_falsify, (generator_arguments, kwargs))[0]
            except Unfalsifiable:
                return
         
            # We run this one final time so we get good errors 
            # Otherwise we would have swallowed all the reports of it actually
            # having gone wrong.
            test(*(arguments + falsifying_example[0]), **falsifying_example[1])
        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__  = test.__doc__
        return wrapped_test
    return run_test_with_generator
