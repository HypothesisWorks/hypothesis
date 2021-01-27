use crate::data::{DataSource, FailedDraw};

use std::cmp::{Ord, Ordering, PartialOrd, Reverse};
use std::collections::BinaryHeap;
use std::mem;

use std::u64::MAX as MAX64;

type Draw<T> = Result<T, FailedDraw>;

pub fn weighted(source: &mut DataSource, probability: f64) -> Result<bool, FailedDraw> {
    // TODO: Less bit-hungry implementation.

    let truthy = (probability * (u64::max_value() as f64 + 1.0)).floor() as u64;
    let probe = source.bits(64)?;
    Ok(match (truthy, probe) {
        (0, _) => false,
        (MAX64, _) => true,
        (_, 0) => false,
        (_, 1) => true,
        _ => probe >= MAX64 - truthy,
    })
}

pub fn bounded_int(source: &mut DataSource, max: u64) -> Draw<u64> {
    let bitlength = 64 - max.leading_zeros() as u64;
    if bitlength == 0 {
        source.write(0)?;
        return Ok(0);
    }
    loop {
        let probe = source.bits(bitlength)?;
        if probe <= max {
            return Ok(probe);
        }
    }
}

#[derive(Debug, Clone)]
pub struct Repeat {
    min_count: u64,
    max_count: u64,
    p_continue: f64,

    current_count: u64,
}

impl Repeat {
    pub fn new(min_count: u64, max_count: u64, expected_count: f64) -> Repeat {
        Repeat {
            min_count,
            max_count,
            p_continue: 1.0 - 1.0 / (1.0 + expected_count),
            current_count: 0,
        }
    }

    pub fn reject(&mut self) {
        assert!(self.current_count > 0);
        self.current_count -= 1;
    }

    pub fn should_continue(&mut self, source: &mut DataSource) -> Result<bool, FailedDraw> {
        if self.min_count == self.max_count {
            if self.current_count < self.max_count {
                self.current_count += 1;
                return Ok(true);
            } else {
                return Ok(false);
            }
        } else if self.current_count < self.min_count {
            source.write(1)?;
            self.current_count += 1;
            return Ok(true);
        } else if self.current_count >= self.max_count {
            source.write(0)?;
            return Ok(false);
        }

        let result = weighted(source, self.p_continue)?;
        if result {
            self.current_count += 1;
        } else {
        }
        Ok(result)
    }
}

#[derive(Debug, Clone)]
struct SamplerEntry {
    primary: usize,
    alternate: usize,
    use_alternate: f32,
}

impl SamplerEntry {
    fn single(i: usize) -> SamplerEntry {
        SamplerEntry {
            primary: i,
            alternate: i,
            use_alternate: 0.0,
        }
    }
}

impl Ord for SamplerEntry {
    fn cmp(&self, other: &SamplerEntry) -> Ordering {
        self.primary
            .cmp(&other.primary)
            .then(self.alternate.cmp(&other.alternate))
    }
}

impl PartialOrd for SamplerEntry {
    fn partial_cmp(&self, other: &SamplerEntry) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for SamplerEntry {
    fn eq(&self, other: &SamplerEntry) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for SamplerEntry {}

#[derive(Debug, Clone)]
pub struct Sampler {
    table: Vec<SamplerEntry>,
}

impl Sampler {
    pub fn new(weights: &[f32]) -> Sampler {
        // FIXME: The correct thing to do here is to allow this,
        // return early, and make this reject the data, but we don't
        // currently have the status built into our data properly...
        assert!(!weights.is_empty());

        let mut table = Vec::new();

        let mut small = BinaryHeap::new();
        let mut large = BinaryHeap::new();

        let total: f32 = weights.iter().sum();

        let mut scaled_probabilities = Vec::new();

        let n = weights.len() as f32;

        for (i, w) in weights.iter().enumerate() {
            let scaled = n * w / total;
            scaled_probabilities.push(scaled);
            if (scaled - 1.0).abs() < f32::EPSILON {
                table.push(SamplerEntry::single(i))
            } else if scaled > 1.0 {
                large.push(Reverse(i));
            } else {
                assert!(scaled < 1.0);
                small.push(Reverse(i));
            }
        }

        while !(small.is_empty() || large.is_empty()) {
            let Reverse(lo) = small.pop().unwrap();
            let Reverse(hi) = large.pop().unwrap();

            assert!(lo != hi);
            assert!(scaled_probabilities[hi] > 1.0);
            assert!(scaled_probabilities[lo] < 1.0);
            scaled_probabilities[hi] = (scaled_probabilities[hi] + scaled_probabilities[lo]) - 1.0;
            table.push(SamplerEntry {
                primary: lo,
                alternate: hi,
                use_alternate: 1.0 - scaled_probabilities[lo],
            });

            if scaled_probabilities[hi] < 1.0 {
                small.push(Reverse(hi))
            } else if scaled_probabilities[hi] > 1.0 {
                large.push(Reverse(hi))
            } else {
                table.push(SamplerEntry::single(hi))
            }
        }
        for &Reverse(i) in small.iter() {
            table.push(SamplerEntry::single(i))
        }
        for &Reverse(i) in large.iter() {
            table.push(SamplerEntry::single(i))
        }

        for ref mut entry in table.iter_mut() {
            if entry.alternate < entry.primary {
                mem::swap(&mut entry.primary, &mut entry.alternate);
                entry.use_alternate = 1.0 - entry.use_alternate;
            }
        }

        table.sort();
        assert!(!table.is_empty());
        Sampler { table }
    }

    pub fn sample(&self, source: &mut DataSource) -> Draw<usize> {
        assert!(!self.table.is_empty());
        let i = bounded_int(source, self.table.len() as u64 - 1)? as usize;
        let entry = &self.table[i];
        let use_alternate = weighted(source, entry.use_alternate as f64)?;
        if use_alternate {
            Ok(entry.alternate)
        } else {
            Ok(entry.primary)
        }
    }
}

pub fn good_bitlengths() -> Sampler {
    let weights = [
        4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, // 1 byte
        2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, // 2 bytes
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, // 3 bytes
        0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, // 4 bytes
        0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, // 5 bytes
        0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, // 6 bytes
        0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, // 7 bytes
        0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, // 8 bytes (last bit spare for sign)
    ];
    assert!(weights.len() == 63);
    Sampler::new(&weights)
}

pub fn integer_from_bitlengths(source: &mut DataSource, bitlengths: &Sampler) -> Draw<i64> {
    let bitlength = bitlengths.sample(source)? as u64 + 1;
    let base = source.bits(bitlength)? as i64;
    let sign = source.bits(1)?;
    if sign > 0 {
        Ok(-base)
    } else {
        Ok(base)
    }
}
