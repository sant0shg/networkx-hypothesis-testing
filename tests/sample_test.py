# contents of example.py
from hypothesis import given, strategies as st

@given(st.integers())
def test_integers(n):
    print(f"called with {n}")
    result = n / 2
    print(f"result is {result}")
    assert n >= 0, "n must be non-negative"

test_integers()