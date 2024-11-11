RELEASE_TYPE: minor

This release improves Hypothesis' handling of ExceptionGroup - it's now able to detect marker detections if they're inside a  group and attempts to resolve them. Note that this handling is still a work in progress and might not handle edge cases optimally. Please open issues if you encounter any problems or unexpected behavior with it.
