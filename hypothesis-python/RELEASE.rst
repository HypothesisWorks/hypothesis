RELEASE_TYPE: patch

This patch improves our type hints for |.filter| to work with |TypeGuard|. For example:

```python
from typing import TypeGuard

from hypothesis import strategies as st


def is_str(x: object) -> TypeGuard[str]:
    return isinstance(x, str)


s = st.from_type(object).filter(is_str)

# previously: SearchStrategy[object]
# now: SearchStrategy[str]
reveal_type(s)
```
