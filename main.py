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


@st.composite
def weighted_graph_and_two_nodes(draw):
    """Random weighted undirected graph + two independently-drawn nodes."""
    n = draw(st.integers(min_value=2, max_value=20))
    edges = draw(st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=n - 1),
            st.integers(min_value=0, max_value=n - 1),
            st.floats(min_value=0.1, max_value=100.0,
                      allow_nan=False, allow_infinity=False),
        ),
        max_size=60,
    ))
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        if u != v:
            G.add_edge(u, v, weight=w)
    nodes = list(G.nodes())
    source = draw(st.sampled_from(nodes))
    target = draw(st.sampled_from(nodes))
    return G, source, target


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


# ---------------------------------------------------------------------------
# Postcondition 1 — Path cost matches the returned distance
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_path_cost_matches_returned_distance(data):
    """
    Postcondition: The sum of edge weights along the returned path equals the
    returned distance for every reachable node.

    Mathematical basis: Dijkstra reports both a distance and a path. These two
    outputs must be consistent: summing the weights along the path must
    reproduce the reported distance exactly.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes, up to
    60 edges, weights in [0.1, 100.0].

    Failure indicates: A mismatch between the path and cost data structures —
    e.g. the path was updated but the distance was not, or vice versa.
    """
    G, source = data
    lengths, paths = nx.single_source_dijkstra(G, source, weight="weight")
    for target, path in paths.items():
        cost = sum(
            G[path[i]][path[i + 1]]["weight"]
            for i in range(len(path) - 1)
        )
        assert abs(cost - lengths[target]) < 1e-9, (
            f"Path cost {cost:.6f} != reported distance {lengths[target]:.6f} "
            f"for {source} -> {target}"
        )


# ---------------------------------------------------------------------------
# Postcondition 2 — Returned paths are structurally valid
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_returned_paths_are_valid(data):
    """
    Postcondition: Every returned path starts at the source, ends at the
    target node, and only traverses edges that exist in the graph.

    Mathematical basis: A valid path is a sequence of nodes where every
    consecutive pair shares an actual edge. Dijkstra must return paths that
    are physically walkable in the graph.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes, up to
    60 edges, weights in [0.1, 100.0].

    Failure indicates: The path-reconstruction step produced a sequence with
    missing edges or wrong endpoints — the path is not actually walkable.
    """
    G, source = data
    _, paths = nx.single_source_dijkstra(G, source, weight="weight")
    for target, path in paths.items():
        assert path[0] == source, (
            f"Path to {target} starts at {path[0]}, expected {source}"
        )
        assert path[-1] == target, (
            f"Path to {target} ends at {path[-1]}, expected {target}"
        )
        for i in range(len(path) - 1):
            assert G.has_edge(path[i], path[i + 1]), (
                f"Path uses non-existent edge ({path[i]}, {path[i + 1]})"
            )


# ---------------------------------------------------------------------------
# Metamorphic 1 — Weight scaling scales distances, preserves paths
# ---------------------------------------------------------------------------

@given(
    weighted_graph_and_node(),
    st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
)
def test_weight_scaling_scales_distances(data, k):
    """
    Metamorphic property: Multiplying all edge weights by a constant k > 0
    multiplies every shortest-path distance by k and leaves the path node
    sequences unchanged.

    Mathematical basis: If path P is optimal for weights w, it is also optimal
    for weights k*w (positive scaling preserves the ordering of path costs).
    The cost of P simply scales by k.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes. The
    scaling factor k is drawn from [0.5, 10.0].

    Failure indicates: Dijkstra's cost accumulation is not linear in edge
    weights, or path selection changes under uniform scaling — neither should
    happen.
    """
    G, source = data
    lengths_orig, paths_orig = nx.single_source_dijkstra(G, source, weight="weight")

    G_scaled = G.copy()
    for u, v in G_scaled.edges():
        G_scaled[u][v]["weight"] = G_scaled[u][v]["weight"] * k

    lengths_scaled, paths_scaled = nx.single_source_dijkstra(G_scaled, source, weight="weight")

    for target in lengths_orig:
        assert abs(lengths_scaled[target] - lengths_orig[target] * k) < 1e-6, (
            f"Scaled distance {lengths_scaled[target]:.6f} != "
            f"{lengths_orig[target]:.6f} * {k:.4f} for {source} -> {target}"
        )
        assert paths_scaled[target] == paths_orig[target], (
            f"Path changed after scaling for {source} -> {target}"
        )


# ---------------------------------------------------------------------------
# Metamorphic 2 — Symmetry on undirected graphs
# ---------------------------------------------------------------------------

@given(weighted_graph_and_two_nodes())
def test_symmetry_on_undirected_graphs(data):
    """
    Metamorphic property: On undirected graphs, dist(u, v) == dist(v, u).

    Mathematical basis: An undirected edge (u, v) can be traversed in either
    direction with the same weight. Any path from u to v can be reversed to
    give a path from v to u with identical total cost.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes. Two
    nodes are drawn independently and may be the same node.

    Failure indicates: The algorithm is treating the undirected graph as
    directed, or the path cost computation is direction-sensitive.
    """
    G, source, target = data
    lengths_from_source = nx.single_source_dijkstra_path_length(G, source, weight="weight")
    lengths_from_target = nx.single_source_dijkstra_path_length(G, target, weight="weight")

    if target in lengths_from_source:
        assert source in lengths_from_target, (
            f"Asymmetric reachability: {source}->{target} reachable but not reverse"
        )
        assert abs(lengths_from_source[target] - lengths_from_target[source]) < 1e-9, (
            f"dist({source},{target})={lengths_from_source[target]:.6f} != "
            f"dist({target},{source})={lengths_from_target[source]:.6f}"
        )
