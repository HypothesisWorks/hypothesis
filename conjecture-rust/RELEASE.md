RELEASE_TYPE: minor

This release improves flexibility and performance of `distributions::Sampler::new` by allowing it to accept `&[f32]` instead of a `Vec`.
It also positively affects `distributions::good_bitlengths` as it does not have to allocate a vector anymore.
