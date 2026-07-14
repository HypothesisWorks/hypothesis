// This file is part of Hypothesis, which may be found at
// https://github.com/HypothesisWorks/hypothesis/
//
// Copyright the Hypothesis Authors.
// Individual contributors are listed in AUTHORS.rst and the git log.
//
// This Source Code Form is subject to the terms of the Mozilla Public License,
// v. 2.0. If a copy of the MPL was not distributed with this file, You can
// obtain one at https://mozilla.org/MPL/2.0/.

#[pyo3::pymodule]
pub(crate) mod cathetus {
    use pyo3::prelude::*;

    /// Given the lengths of the hypotenuse and a side of a right triangle,
    /// return the length of the other side.
    ///
    /// A companion to the C99 `hypot()` function. Some care is needed to avoid
    /// underflow in the case of small arguments, and overflow in the case of
    /// large arguments as would occur for the naive implementation as
    /// `sqrt(h*h - a*a)`. The behaviour with respect to non-finite arguments
    /// (NaNs and infinities) is designed to be as consistent as possible with
    /// the C99 `hypot()` specifications.
    ///
    /// This function relies on the platform `sqrt` and so, like it, may be
    /// inaccurate up to a relative error of (around) floating-point epsilon.
    ///
    /// Based on the C99 implementation https://gitlab.com/jjg/cathetus
    #[pyfunction]
    pub fn cathetus(h: f64, a: f64) -> f64 {
        if h.is_nan() {
            return f64::NAN;
        }
        if h.is_infinite() {
            // Deliberately includes the case when a.is_nan(), because the
            // C99 standard mandates that hypot(inf, nan) == inf
            return if a.is_infinite() {
                f64::NAN
            } else {
                f64::INFINITY
            };
        }

        let h = h.abs();
        let a = a.abs();

        if h < a {
            return f64::NAN;
        }

        // Thanks to floating-point precision issues when performing multiple
        // operations on extremely large or small values, we may rarely calculate
        // a side length that is longer than the hypotenuse. This is clearly an
        // error, so we clip to the hypotenuse as the best available estimate.
        let sqrt_max = f64::MAX.sqrt();
        let sqrt_min = f64::MIN_POSITIVE.sqrt();
        let b = if h > sqrt_max {
            if h > f64::MAX / 2.0 {
                (h - a).sqrt() * (h / 2.0 + a / 2.0).sqrt() * 2f64.sqrt()
            } else {
                (h - a).sqrt() * (h + a).sqrt()
            }
        } else if h < sqrt_min {
            (h - a).sqrt() * (h + a).sqrt()
        } else {
            ((h - a) * (h + a)).sqrt()
        };
        // Propagate NaN, matching Python's `min(b, h)` semantics.
        if b.is_nan() {
            f64::NAN
        } else {
            b.min(h)
        }
    }
}
