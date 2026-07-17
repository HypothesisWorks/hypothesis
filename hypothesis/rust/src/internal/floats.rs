// This file is part of Hypothesis, which may be found at
// https://github.com/HypothesisWorks/hypothesis/
//
// Copyright the Hypothesis Authors.
// Individual contributors are listed in AUTHORS.rst and the git log.
//
// This Source Code Form is subject to the terms of the Mozilla Public License,
// v. 2.0. If a copy of the MPL was not distributed with this file, You can
// obtain one at https://mozilla.org/MPL/2.0/.

mod f16_conv {
    const F64_MANTISSA_MASK: u64 = (1 << 52) - 1;
    const F64_IMPLICIT_BIT: u64 = 1 << 52;
    const F16_SIGN_BIT: u16 = 0x8000;
    const F16_INF_BITS: u16 = 0x7c00;
    const F16_QUIET_NAN_BIT: u16 = 0x0200;

    /// Narrow an `f64` to IEEE 754 half-precision, returning the raw 16 bits.
    /// Round-to-nearest-even; finite values too large for the format become
    /// infinity (the caller decides whether that is an error).
    pub(crate) fn f16_bits_from_f64(value: f64) -> u16 {
        let x = value.to_bits();
        // shift f64's sign bit (bit 63) down to f16's (bit 15)
        let sign = ((x >> 48) as u16) & F16_SIGN_BIT;
        let biased = ((x >> 52) & 0x7ff) as i32;
        let mant = x & F64_MANTISSA_MASK;

        // inf / nan
        if biased == 0x7ff {
            return sign | F16_INF_BITS | if mant != 0 { F16_QUIET_NAN_BIT } else { 0 };
        }
        // +/- 0
        if biased == 0 && mant == 0 {
            return sign;
        }

        // rebias the exponent from f64 (bias 1023) to f16 (bias 15)
        let e = biased - 1023 + 15;

        // overflow to infinity
        if e >= 0x1f {
            return sign | F16_INF_BITS;
        }

        // subnormal or underflow in f16
        if e <= 0 {
            // magnitude below half of the smallest subnormal rounds to zero
            if e < -10 {
                return sign;
            }
            // restore the implicit leading 1, then round-to-nearest-even while
            // shifting the 53-bit significand down to the subnormal position
            let sig = mant | F64_IMPLICIT_BIT;
            let shift = (43 - e) as u32;
            let half = 1u64 << (shift - 1);
            let low = sig & ((1u64 << shift) - 1);
            let mut result = (sig >> shift) as u16;
            if low > half || (low == half && result & 1 == 1) {
                result += 1;
            }
            return sign | result;
        }

        // normal: keep 10 mantissa bits, round-to-nearest-even on the rest
        let shift = 42u32;
        let half = 1u64 << (shift - 1);
        let low = mant & ((1u64 << shift) - 1);
        let mut m = (mant >> shift) as u16;
        let mut e = e as u16;
        if low > half || (low == half && m & 1 == 1) {
            m += 1;
            if m == 0x400 {
                // mantissa carried into the exponent
                m = 0;
                e += 1;
                if e >= 0x1f {
                    return sign | F16_INF_BITS;
                }
            }
        }
        sign | (e << 10) | m
    }

    /// Widen the raw 16 bits of an IEEE 754 half-precision float to `f64`.
    pub(crate) fn f16_bits_to_f64(bits: u16) -> f64 {
        let sign = if bits & F16_SIGN_BIT != 0 { -1.0 } else { 1.0 };
        let exp = (bits >> 10) & 0x1f;
        let mant = bits & 0x3ff;
        let magnitude = match exp {
            0 => (mant as f64) * 2f64.powi(-24),
            0x1f => {
                if mant == 0 {
                    f64::INFINITY
                } else {
                    f64::NAN
                }
            }
            _ => (1.0 + (mant as f64) / 1024.0) * 2f64.powi(exp as i32 - 15),
        };
        magnitude.copysign(sign)
    }
}

#[cfg(test)]
#[path = "../../tests/embedded/internal/test_floats.rs"]
mod tests;

#[pyo3::pymodule]
pub(crate) mod floats {
    use super::f16_conv::{f16_bits_from_f64, f16_bits_to_f64};
    use pyo3::exceptions::PyOverflowError;
    use pyo3::prelude::*;

    #[pyfunction]
    fn float_of(x: f64, width: u32) -> PyResult<f64> {
        assert!(matches!(width, 16 | 32 | 64));
        if width == 64 {
            Ok(x)
        } else if width == 32 {
            int_to_float(float_to_int(x, 32)?, 32)
        } else {
            int_to_float(float_to_int(x, 16)?, 16)
        }
    }

    #[pyfunction]
    fn is_negative(x: f64) -> bool {
        x.is_sign_negative()
    }

    #[pyfunction]
    #[pyo3(signature = (x, y, width=64))]
    fn count_between_floats(x: f64, y: f64, width: u32) -> PyResult<u64> {
        assert!(x <= y);
        if is_negative(x) {
            if is_negative(y) {
                Ok(float_to_int(x, width)? - float_to_int(y, width)? + 1)
            } else {
                Ok(count_between_floats(x, -0.0, width)? + count_between_floats(0.0, y, width)?)
            }
        } else {
            assert!(!is_negative(y));
            Ok(float_to_int(y, width)? - float_to_int(x, width)? + 1)
        }
    }

    #[pyfunction]
    #[pyo3(signature = (value, width=64))]
    fn float_to_int(value: f64, width: u32) -> PyResult<u64> {
        match width {
            16 => {
                let h = f16_bits_from_f64(value);
                if value.is_finite() && f16_bits_to_f64(h).is_infinite() {
                    return Err(PyOverflowError::new_err("float too large to pack"));
                }
                Ok(h as u64)
            }
            32 => {
                let f = value as f32;
                if value.is_finite() && f.is_infinite() {
                    return Err(PyOverflowError::new_err("float too large to pack"));
                }
                Ok(f.to_bits() as u64)
            }
            64 => Ok(value.to_bits()),
            _ => unreachable!(),
        }
    }

    #[pyfunction]
    #[pyo3(signature = (value, width=64))]
    fn int_to_float(value: u64, width: u32) -> PyResult<f64> {
        match width {
            16 => Ok(f16_bits_to_f64(u16::try_from(value).unwrap())),
            32 => Ok(f32::from_bits(u32::try_from(value).unwrap()) as f64),
            64 => Ok(f64::from_bits(value)),
            _ => unreachable!(),
        }
    }

    /// Return the first float larger than finite `val` - IEEE 754's `nextUp`.
    ///
    /// Adapted from https://stackoverflow.com/a/10426033, with thanks to Mark Dickinson.
    #[pyfunction]
    #[pyo3(signature = (value, width=64))]
    fn next_up(value: f64, width: u32) -> PyResult<f64> {
        if value.is_nan() || (value.is_infinite() && value > 0.0) {
            return Ok(value);
        }
        if value == 0.0 && is_negative(value) {
            return Ok(0.0);
        }
        let bits = float_to_int(value, width)?;
        // Note: n is signed; float_to_int returns unsigned
        let shift = 64 - width;
        let n = ((bits << shift) as i64) >> shift;
        let n = if n >= 0 {
            n.strict_add(1)
        } else {
            n.strict_sub(1)
        };
        // n still fits inside `width` bits
        assert!((n << shift) >> shift == n);
        int_to_float(n as u64 & (u64::MAX >> shift), width)
    }

    #[pyfunction]
    #[pyo3(signature = (value, width=64))]
    fn next_down(value: f64, width: u32) -> PyResult<f64> {
        Ok(-next_up(-value, width)?)
    }

    #[pyfunction]
    #[pyo3(signature = (value, width, *, allow_subnormal))]
    fn next_down_normal(value: f64, width: u32, allow_subnormal: bool) -> PyResult<f64> {
        let value = next_down(value, width)?;
        if (!allow_subnormal) && 0.0 < value.abs() && value.abs() < width_smallest_normals(width) {
            return Ok(if value > 0.0 {
                0.0
            } else {
                -width_smallest_normals(width)
            });
        }
        Ok(value)
    }

    #[pyfunction]
    #[pyo3(signature = (value, width, *, allow_subnormal))]
    fn next_up_normal(value: f64, width: u32, allow_subnormal: bool) -> PyResult<f64> {
        Ok(-next_down_normal(-value, width, allow_subnormal)?)
    }

    // Smallest positive non-zero numbers that is fully representable by an
    // IEEE-754 float, calculated with the width's associated minimum exponent.
    // Values from https://en.wikipedia.org/wiki/IEEE_754#Basic_and_interchange_formats
    #[pyfunction]
    fn width_smallest_normals(width: u32) -> f64 {
        match width {
            16 => 2f64.powi(-(2i32.pow(5 - 1) - 2)),
            32 => 2f64.powi(-(2i32.pow(8 - 1) - 2)),
            64 => 2f64.powi(-(2i32.pow(11 - 1) - 2)),
            _ => unreachable!(),
        }
    }
}
