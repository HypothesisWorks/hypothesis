// This file is part of Hypothesis, which may be found at
// https://github.com/HypothesisWorks/hypothesis/
//
// Copyright the Hypothesis Authors.
// Individual contributors are listed in AUTHORS.rst and the git log.
//
// This Source Code Form is subject to the terms of the Mozilla Public License,
// v. 2.0. If a copy of the MPL was not distributed with this file, You can
// obtain one at https://mozilla.org/MPL/2.0/.

use super::f16_conv::*;
use half::f16;

fn assert_narrowing_matches(x: f64) {
    let ours = f16_bits_from_f64(x);
    // `half` rounds incorrectly near rounding ties:
    //   * https://github.com/VoidStarKat/half-rs/issues/116
    //   * https://github.com/VoidStarKat/half-rs/issues/151
    //
    // We skip the test on inputs which hit these bugs.
    let truncated = f64::from_bits(x.to_bits() & !0xffff_ffff);
    let via_f32 = (x as f32) as f64;
    if !x.is_nan() && (f16_bits_from_f64(truncated) != ours || f16_bits_from_f64(via_f32) != ours) {
        return;
    }

    if x.is_nan() {
        let ours = f16::from_bits(ours);
        assert!(ours.is_nan(), "x={:#018x}", x.to_bits());
        assert_eq!(
            ours.is_sign_negative(),
            x.is_sign_negative(),
            "x={:#018x}",
            x.to_bits()
        );
    } else {
        assert_eq!(
            ours,
            f16::from_f64(x).to_bits(),
            "x={x} ({:#018x})",
            x.to_bits()
        );
    }
}

#[test]
fn widening_matches_half() {
    for bits in 0..=u16::MAX {
        let a = f16_bits_to_f64(bits);
        let b = f16::from_bits(bits).to_f64();
        if b.is_nan() {
            assert!(a.is_nan(), "bits={bits:#06x}");
            assert_eq!(
                a.is_sign_negative(),
                b.is_sign_negative(),
                "bits={bits:#06x}"
            );
        } else {
            assert_eq!(a.to_bits(), b.to_bits(), "bits={bits:#06x}");
        }
    }
}

#[test]
fn narrowing_matches_half() {
    for _ in 0..1_000_000 {
        assert_narrowing_matches(f64::from_bits(rand::random()));
    }
}

/// explicit check to actual bits without comparing to `half`, which is incorrect in some cases
/// for rounding near ties
#[test]
fn narrowing_rounds_ties_correctly() {
    let check = |x: f64, expected: u16| {
        assert_eq!(
            f16_bits_from_f64(x),
            expected,
            "x={x} ({:#018x})",
            x.to_bits()
        );
        assert_eq!(
            f16_bits_from_f64(-x),
            0x8000 | expected,
            "x={} ({:#018x})",
            -x,
            (-x).to_bits()
        );
    };

    for bits in 0..f16::MAX.to_bits() {
        let mid = (f16_bits_to_f64(bits) + f16_bits_to_f64(bits + 1)) / 2.0;
        let even = if bits & 1 == 0 { bits } else { bits + 1 };
        check(mid, even);
        check(f64::from_bits(mid.to_bits() + 1), bits + 1);
        check(f64::from_bits(mid.to_bits() - 1), bits);
    }
    // the overflow tie, halfway between f16::MAX and 2^16, rounds to infinity
    check(65520.0, 0x7c00);
    check(f64::from_bits(65520f64.to_bits() + 1), 0x7c00);
    check(f64::from_bits(65520f64.to_bits() - 1), 0x7bff);
}

/// explicitly cover some rare cases that are possible-but-rare in narrowing_matches_half
#[test]
fn narrowing_matches_half_explicit() {
    // all 65536 f16 values, widened to their f64 values
    let mut cases: Vec<f64> = (0..=u16::MAX).map(f16_bits_to_f64).collect();

    // midpoint values between adjacent f16 values. Tests rounding behavior when the f64
    // float can't be exactly represented
    for bits in 0..f16::MAX.to_bits() {
        let mid = (f16_bits_to_f64(bits) + f16_bits_to_f64(bits + 1)) / 2.0;
        cases.push(mid);
        cases.push(-mid);
    }

    // halfway between f16::MAX and 2^16
    let overflow_tie = (f16::MAX.to_f64() + 2f64.powi(16)) / 2.0;
    assert_eq!(overflow_tie, 65520.0);
    cases.push(overflow_tie);
    cases.push(-overflow_tie);

    for x in cases.clone() {
        let bits = x.to_bits();
        cases.push(f64::from_bits(bits.wrapping_add(1)));
        cases.push(f64::from_bits(bits.wrapping_sub(1)));
    }

    for x in cases {
        assert_narrowing_matches(x);
    }
}
