from hypothesis import given, strategies as st


@given(st.integers(min_value=0, max_value=10))
def test_single_draw(n):
    print(f"n = {n}")
    assert 0 <= n <= 10

# Using draw
@st.composite
def list_of_n_integers(draw):
    n = draw(st.integers(min_value=1, max_value=5))
    print(f"drew n = {n}")

    return n


@given(list_of_n_integers())
def test_list_length_matches_n(n):
    assert 1 <= n <= 5