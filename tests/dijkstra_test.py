"""
Property-Based Tests: Dijkstra's Shortest Path — Invariants
Algorithm: networkx.algorithms.shortest_paths.weighted.single_source_dijkstra
Reference: https://networkx.org/documentation/stable/reference/algorithms/shortest_paths/dijkstra.html

Precondition enforced by the graph strategy: all edge weights >= 0.
"""

import networkx as nx
from hypothesis import given, strategies as st


# ---------------------------------------------------------------------------
# Graph generation strategy — weighted, non-negative edges
# ---------------------------------------------------------------------------

@st.composite
def weighted_graph_and_node(draw):
    """Generate a random weighted undirected graph and one of its nodes."""
    n = draw(st.integers(min_value=2, max_value=20))

    edges = draw(st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=n - 1),   # u
            st.integers(min_value=0, max_value=n - 1),   # v
            st.floats(min_value=0.1, max_value=100.0,    # weight (non-negative)
                      allow_nan=False, allow_infinity=False),
        ),
        max_size=60,
    ))

    G = nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        if u != v:
            G.add_edge(u, v, weight=w)

    # Pick any node from the graph to use as the source
    source = draw(st.sampled_from(list(G.nodes())))
    return G, source


# ---------------------------------------------------------------------------
# Invariant — Self-distance is always 0
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_self_distance_is_zero(data):
    """
    Invariant: The shortest path distance from any node to itself is always 0.

    Mathematical basis: A path from v to v with no edges has total weight 0.
    Dijkstra must never assign a positive cost to this trivial path, regardless
    of edge weights or graph structure.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes and up
    to 60 edges. All weights are in [0.1, 100.0] to satisfy Dijkstra's
    non-negative weight precondition.

    Failure indicates: The algorithm initialises distances incorrectly, or a
    relaxation step corrupts the distance of the source node itself.
    """
    G, source = data
    lengths = nx.single_source_dijkstra_path_length(G, source, weight="weight")
    assert lengths[source] == 0.0, (
        f"Self-distance of node {source} is {lengths[source]}, expected 0.0"
    )


# ---------------------------------------------------------------------------
# Invariant — All distances are non-negative
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_all_distances_are_non_negative(data):
    """
    Invariant: Every distance returned by Dijkstra is >= 0.

    Mathematical basis: Each edge weight is >= 0 (enforced by the strategy),
    so any path cost is a sum of non-negative numbers, which is itself
    non-negative. Dijkstra cannot produce a negative distance when all weights
    satisfy the precondition.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes and up
    to 60 edges. All weights are in [0.1, 100.0], so the precondition is always
    satisfied. Only reachable nodes appear in the result dict, so every entry
    must have a non-negative cost.

    Failure indicates: A relaxation step subtracted instead of added weight, or
    the initialisation set a node's distance to a negative sentinel value that
    was never overwritten.
    """
    G, source = data
    lengths = nx.single_source_dijkstra_path_length(G, source, weight="weight")
    for node, dist in lengths.items():
        assert dist >= 0.0, (
            f"Node {node} has negative distance {dist} from source {source}"
        )
