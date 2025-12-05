# Hypothesis Development Guide

## Essential Reading

**Always read `CONTRIBUTING.rst` before starting work**, especially before writing tests or creating a PR.

## Testing

### Running Tests

Run tests using the build system:
- **Quick test run**: `./build.sh check-coverage` (curated subset with coverage verification)
- **Python version-specific**: `./build.sh check-py311` (replace with target version)
- **Fine-grained control**: `./build.sh tox py311-custom 3.11.3 -- [pytest args]`
- **Direct pytest** (after setup): `pytest hypothesis-python/tests/cover/`

### Writing Tests

**Never use `.example()` method in tests.** Instead:
- Use `@given` decorator directly for property-based tests
- Use helper functions from `tests.common.debug`:
  - `minimal()` - find minimal failing example
  - `find_any()` - find any example matching condition
  - `assert_all_examples()` - verify all examples match predicate
  - `assert_simple_property()` - verify simple properties with few examples
  - `check_can_generate_examples()` - verify strategy can generate without error

## Changelog & Pull Requests

When creating a PR that changes `hypothesis-python/src/`:
1. Create `hypothesis-python/RELEASE.rst` with `RELEASE_TYPE: patch` (bugfixes) or `minor` (features)
2. See `RELEASE-sample.rst` for examples
3. **Imitate the style in `changelog.rst`** for consistency
4. Follow all changelog instructions in `CONTRIBUTING.rst`

**Note:** Test-only changes (no modifications to `src/`) do not require a RELEASE.rst file.

## Before Committing

1. Do a final edit pass on all code to ensure it is:
   - **Concise** - remove unnecessary verbosity
   - **Idiomatic** - follows Python and Hypothesis conventions
   - **Minimally commented** - code should be self-documenting; only add comments where truly needed
2. **Run `./build.sh format; ./build.sh lint`** immediately before committing to auto-format and lint code
3. **Do not reference issues or PRs in commit messages** (e.g., avoid `Fixes #1234` or `See #5678`) - this clutters the issue timeline with unnecessary links
