# Learnings from Issue #4466: Accept Fraction as bounds in st.decimals()

## Issue Summary
Users wanted to pass `Fraction` objects as bounds to `st.decimals()`, but it was failing with a type conversion error. The request was to handle fractions similar to how `st.integers()` does - accepting them when they can be precisely represented.

## Key Technical Insights

### 1. Decimal Precision Context
The `_as_finite_decimal()` function uses `localcontext(Context())` to ensure default traps are enabled. This is critical for detecting precision issues during conversion. The initial implementation had the Fraction conversion outside this context, which caused issues because:
- Division can trigger inexact operation traps
- The conversion needed to happen inside the context to maintain consistency with other conversions

### 2. Fraction to Decimal Conversion
Cannot use `Decimal(fraction)` directly - the Decimal constructor doesn't accept Fraction objects. Instead:
```python
decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
```

### 3. Precision Verification
After converting, verify the conversion is lossless by converting back:
```python
if Fraction(decimal_value) != original:
    raise InvalidArgument(...)
```

This catches fractions like `Fraction(1, 3)` which would lose precision.

### 4. Strategy Composition
The `decimals()` strategy internally uses `fractions()` when `places` is not specified (line 1806). This means:
- When we pass Fraction bounds, they get converted to Decimal by `_as_finite_decimal()`
- Then passed to `fractions()` which can accept Decimals
- The fractions strategy generates Fraction values
- These get converted to Decimals via `fraction_to_decimal`

This composition means Fraction bounds work seamlessly once the initial conversion is handled.

### 5. Default NaN Behavior
When `max_value` is None, `allow_nan` defaults to True (line 1809 in decimals()):
```python
if allow_nan or (allow_nan is None and (None in (min_value, max_value))):
```
This explains why initial tests without `allow_nan=False` were generating NaN values.

## Testing Best Practices

### Property-Based Testing Over Examples
Instead of testing specific cases like `Fraction(1, 2)`, `Fraction(1, 4)`, etc., use property-based tests:
- Draw random decimal bounds
- Convert to fractions
- Create strategy with fraction bounds
- Verify results are within original decimal bounds

This provides much better coverage and tests the actual property: "Fractions that represent precise decimals should work as bounds."

### Use Helper Functions
Use `check_can_generate_examples()` instead of `.example()` for error testing. This is:
- More robust
- Tests the strategy validation, not just example generation
- Consistent with the rest of the test suite

### Avoid Redundant Tests
The simple test `decimals(min_value=Fraction(850))` was redundant because:
- The @given test with Fraction bounds already covers this
- The property-based test covers a superset of cases

## Code Style Learnings

### Comments Should Explain Why, Not What
- Remove comments that just describe what the code does
- Keep comments that explain non-obvious reasoning (like "This could be infinity, quiet NaN, or signalling NaN")
- The context managers and control flow should be self-documenting

### Error Messages
Keep error messages concise but informative:
- ✅ "Cannot convert {name}={value!r} to Decimal without loss of precision"
- ❌ "Cannot convert {name}={value!r} of type {type(value).__name__} to type Decimal without loss of precision"

The type information is often redundant since the repr already shows it.

### Idiomatic Python
Store the original value when you need it for error messages:
```python
if isinstance(value, Fraction):
    original = value
    value = Decimal(value.numerator) / Decimal(value.denominator)
    if Fraction(value) != original:
        raise InvalidArgument(f"... {original!r} ...")
```

## Changelog Entry Format
Hypothesis uses a specific format for RELEASE.rst:
- First line: `RELEASE_TYPE: minor` (or patch/major)
- Use Sphinx cross-references: `:func:`, `:class:`, `:issue:`
- Describe what changed in the public API and why
- Keep it concise and user-focused
- Minor = new feature, patch = bugfix, major = breaking change

## Development Workflow
1. Understand the issue thoroughly before coding
2. Look at similar existing code (like `st.integers()` handling fractions)
3. Write implementation
4. Write tests (property-based when possible)
5. Test manually to verify
6. Refactor for clarity and idiomaticity
7. Write changelog entry
8. Commit with descriptive message
9. Push to feature branch

## Files Changed
- `hypothesis-python/src/hypothesis/strategies/_internal/core.py` - Added Fraction handling in `_as_finite_decimal()`
- `hypothesis-python/tests/cover/test_numerics.py` - Added tests for Fraction bounds
- `hypothesis-python/RELEASE.rst` - Changelog entry
