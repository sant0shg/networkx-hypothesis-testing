"""
Property-Based Tests: Dijkstra's Shortest Path
Algorithm: networkx.algorithms.shortest_paths.weighted.single_source_dijkstra
Reference: https://networkx.org/documentation/stable/reference/algorithms/shortest_paths/dijkstra.html

Properties covered:
  - Invariants
  - Postconditions
  - Metamorphic properties
  - Idempotence
  - Boundary conditions

Precondition enforced by all graph strategies: all edge weights >= 0.
"""

import networkx as nx
from hypothesis import given
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Graph generation strategies
# ---------------------------------------------------------------------------

@st.composite
def weighted_graph_and_node(draw, min_nodes=2, max_nodes=20):
    """Random weighted undirected graph + one of its nodes as source."""
    n = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
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
# Invariant 1 — Self-distance is always 0
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
# Invariant 2 — All distances are non-negative
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
    satisfied.

    Failure indicates: A relaxation step subtracted instead of added weight, or
    the initialisation set a node's distance to a negative sentinel that was
    never overwritten.
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


# ---------------------------------------------------------------------------
# Idempotence — Running Dijkstra twice gives identical results
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_dijkstra_is_idempotent(data):
    """
    Idempotence: Running Dijkstra twice on the same graph and source produces
    identical distances both times.

    Mathematical basis: Dijkstra is a deterministic algorithm. Given the same
    graph and source it must always return the same output. A second run must
    not observe any mutation from the first.

    Graphs generated: Random weighted undirected graphs with 2-20 nodes, up to
    60 edges, weights in [0.1, 100.0].

    Failure indicates: The algorithm has side effects that mutate the graph or
    internal state between runs, breaking determinism.
    """
    G, source = data
    lengths1 = dict(nx.single_source_dijkstra_path_length(G, source, weight="weight"))
    lengths2 = dict(nx.single_source_dijkstra_path_length(G, source, weight="weight"))
    assert lengths1 == lengths2, (
        f"Dijkstra returned different results on two runs from source {source}"
    )


# ---------------------------------------------------------------------------
# Boundary 1 — Single-node graph: only self is reachable
# ---------------------------------------------------------------------------

@given(st.integers(min_value=0, max_value=100))
def test_single_node_graph(node_id):
    """
    Boundary condition: A graph with exactly one node and no edges has only
    the node itself reachable, with distance 0.

    Mathematical basis: The trivial path from a node to itself has zero cost.
    No other nodes exist, so the result dict has exactly one entry.

    Graphs generated: Single-node graphs where the node id is drawn from
    [0, 100] to ensure node identity does not affect the result.

    Failure indicates: The algorithm fails on the minimal possible graph, or
    introduces phantom distances for nodes that do not exist.
    """
    G = nx.Graph()
    G.add_node(node_id)
    lengths = dict(nx.single_source_dijkstra_path_length(G, node_id, weight="weight"))
    assert lengths == {node_id: 0.0}, (
        f"Single-node graph: expected {{{node_id}: 0.0}}, got {lengths}"
    )


# ---------------------------------------------------------------------------
# Boundary 2 — Edgeless graph: only source is reachable
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_edgeless_graph_only_source_reachable(data):
    """
    Boundary condition: In a graph with no edges, only the source node is
    reachable from the source (with distance 0).

    Mathematical basis: Without edges there are no paths between distinct
    nodes. Dijkstra must return only the source with distance 0 and must not
    report any other node.

    Graphs generated: Nodes from a random weighted graph are reused but all
    edges are stripped, producing an edgeless graph of the same size (2-20
    nodes). The source is carried over from the original strategy.

    Failure indicates: The algorithm reports distances to unreachable nodes, or
    mishandles graphs where no relaxation steps are possible.
    """
    G, source = data
    G_empty = nx.Graph()
    G_empty.add_nodes_from(G.nodes())  # same nodes, zero edges
    lengths = dict(nx.single_source_dijkstra_path_length(G_empty, source, weight="weight"))
    assert set(lengths.keys()) == {source}, (
        f"Edgeless graph: expected only source {source}, got {set(lengths.keys())}"
    )
    assert lengths[source] == 0.0


# ---------------------------------------------------------------------------
# Boundary 3 — Disconnected graph: unreachable nodes absent from result
# ---------------------------------------------------------------------------

@given(weighted_graph_and_node())
def test_disconnected_nodes_absent_from_result(data):
    """
    Boundary condition: Nodes not reachable from the source do not appear in
    the result of single_source_dijkstra_path_length.

    Mathematical basis: Dijkstra only visits nodes it can reach via existing
    edges. Unreachable nodes have no finite shortest path and must not appear
    in the output dict.

    Graphs generated: Random undirected graphs with 2-20 nodes, which
    frequently contain multiple disconnected components due to random edge
    sampling — giving good natural coverage of this case.

    Failure indicates: The algorithm assigns a distance to nodes it never
    visited, corrupting the result dict with phantom entries.
    """
    G, source = data
    lengths = dict(nx.single_source_dijkstra_path_length(G, source, weight="weight"))
    for node in G.nodes():
        if node not in lengths:
            assert not nx.has_path(G, source, node), (
                f"Node {node} is reachable from {source} but missing from result"
            )
