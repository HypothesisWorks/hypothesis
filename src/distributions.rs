use data::{DataSource, FailedDraw};

pub fn weighted(source: &mut DataSource, probability: f64) -> Result<bool, FailedDraw> {
    // TODO: Less bit-hungry implementation.

    let truthy = (probability * (u64::max_value() as f64 + 1.0)).floor() as u64;
    let probe = source.bits(64)?;
    return Ok(probe >= u64::max_value() - truthy + 1);
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
            min_count: min_count,
            max_count: max_count,
            p_continue: 1.0 - 1.0 / (1.0 + expected_count),
            current_count: 0,
        }
    }

    fn draw_until(&self, source: &mut DataSource, value: bool) -> Result<(), FailedDraw> {
        // Force a draw until we get the desired outcome. By having this we get much better
        // shrinking when min_size or max_size are set because all decisions are represented
        // somewhere in the bit stream.
        loop {
            let d = weighted(source, self.p_continue)?;
            if d == value {
                return Ok(());
            }
        }
    }

    pub fn should_continue(&mut self, source: &mut DataSource) -> Result<bool, FailedDraw> {
        let result = if self.current_count < self.min_count {
            self.draw_until(source, true)?;
            return Ok(true);
        } else if self.current_count >= self.max_count {
            self.draw_until(source, false)?;
            return Ok(false);
        } else {
            weighted(source, self.p_continue)
        };

        match result {
            Ok(true) => self.current_count += 1,
            _ => (),
        }
        return result;
    }
}
