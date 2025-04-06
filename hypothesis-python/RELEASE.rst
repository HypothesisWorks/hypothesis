RELEASE_TYPE: patch

When reporting the always-failing, never-passing lines from the |Phase.explain| phase, we now sort the reported lines so that local code shows up first, then third-party library code, then standard library code.
