pub fn minimize_integer<F, T>(start: u64, mut criterion: F) -> Result<u64, T>
where
    F: FnMut(u64) -> Result<bool, T>,
{
    if start == 0 {
        Ok(start)
    } else if criterion(0)? {
        Ok(0)
    } else {
        let mut lo = 0;
        let mut hi = start;
        while lo + 1 < hi {
            let mid = lo + (hi - lo) / 2;
            if criterion(mid)? {
                hi = mid;
            } else {
                lo = mid;
            }
        }

        Ok(hi)
    }
}
