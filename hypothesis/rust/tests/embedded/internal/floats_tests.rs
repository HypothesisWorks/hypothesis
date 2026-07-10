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

#[test]
fn widening_matches_half() {
    for bits in 0..=u16::MAX {
        let ours = f16_bits_to_f64(bits);
        let oracle = f16::from_bits(bits).to_f64();
        if oracle.is_nan() {
            assert!(ours.is_nan(), "bits={bits:#06x}");
            assert_eq!(
                ours.is_sign_negative(),
                oracle.is_sign_negative(),
                "bits={bits:#06x}"
            );
        } else {
            assert_eq!(ours.to_bits(), oracle.to_bits(), "bits={bits:#06x}");
        }
    }
}

#[test]
fn narrowing_matches_half() {
    for _ in 0..1_000_000 {
        let x = f64::from_bits(rand::random());
        let ours = f16_bits_from_f64(x);
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
}
