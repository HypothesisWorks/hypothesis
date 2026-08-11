RELEASE_TYPE: patch

This patch fixes ``BytestringProvider.draw_float`` so that it can generate
negative floats. Previously, only 64 bits were drawn for a 65-bit float index
format, so the sign bit was always zero and negative floats could never be
produced.