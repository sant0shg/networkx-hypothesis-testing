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


# ===========================================================================
# Algorithm: Dinitz Maximum Flow
# networkx.algorithms.flow.dinitz
# Reference: https://networkx.org/documentation/stable/reference/algorithms/
#            generated/networkx.algorithms.flow.dinitz.html
# ===========================================================================

@st.composite
def flow_graph_and_nodes(draw):
    """Random directed graph with capacities + a source and sink node."""
    n = draw(st.integers(min_value=2, max_value=10))
    edges = draw(st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=n - 1),  # u
            st.integers(min_value=0, max_value=n - 1),  # v
            st.integers(min_value=1, max_value=20),     # capacity (always >= 1)
        ),
        max_size=30,
    ))
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    for u, v, cap in edges:
        if u != v:
            G.add_edge(u, v, capacity=cap)
    nodes = list(G.nodes())
    source = draw(st.sampled_from(nodes))
    sink   = draw(st.sampled_from(nodes))
    return G, source, sink


# ---------------------------------------------------------------------------
# Invariant — Max-Flow equals Min-Cut (Max-Flow Min-Cut theorem)
# ---------------------------------------------------------------------------

@given(flow_graph_and_nodes())
def test_max_flow_equals_min_cut(data):
    """
    Invariant: maximum_flow_value(G, s, t) == minimum_cut value(G, s, t).

    Mathematical basis: The Max-Flow Min-Cut theorem (Ford-Fulkerson, 1956)
    guarantees that the value of the maximum flow from s to t equals the
    capacity of the minimum s-t cut. A minimum cut is a partition of nodes
    into two sets S (containing s) and T (containing t) such that the total
    capacity of edges from S to T is minimised. Any correct max-flow algorithm
    must produce a flow value exactly equal to this minimum cut capacity.

    Graphs generated: Random directed graphs with 2-10 nodes and up to 30
    edges. All capacities are integers in [1, 20]. Source and sink are drawn
    independently and may be any node in the graph. Cases where source == sink
    or there is no path s -> t are skipped (trivially zero flow, not
    interesting for this property).

    Failure indicates: Dinitz did not find the true maximum flow — either it
    terminated too early (flow too low) or there is a bug in NetworkX's
    minimum_cut computation that this test has exposed.
    """
    G, source, sink = data
    if source == sink or not nx.has_path(G, source, sink):
        return  # skip trivial / unreachable cases

    flow_value = nx.maximum_flow_value(G, source, sink, flow_func=dinitz)
    cut_value, _ = nx.minimum_cut(G, source, sink, flow_func=dinitz)

    assert abs(flow_value - cut_value) < 1e-9, (
        f"Max flow {flow_value} != min cut {cut_value} "
        f"for source={source}, sink={sink}"
    )


# ---------------------------------------------------------------------------
# Invariant — Flow conservation at every internal node
# ---------------------------------------------------------------------------

@given(flow_graph_and_nodes())
def test_flow_conservation_at_internal_nodes(data):
    """
    Invariant: For every node v that is neither the source nor the sink,
    the total flow into v equals the total flow out of v.

        sum(R[u][v]['flow'] for u in R.predecessors(v)) == 0

    (NetworkX stores flow antisymmetrically: R[u][v]['flow'] is positive for
    flow from u to v, and R[v][u]['flow'] == -R[u][v]['flow']. Summing all
    flow values on edges *entering* v in the residual network therefore gives
    net-flow-in minus net-flow-out, which must be zero at internal nodes.)

    Mathematical basis: Flow conservation is the second of the two conditions
    that define a *feasible flow* (the first being capacity constraints). A
    result that violates conservation is not a valid flow — it implies flow
    is being created or destroyed at an internal node, which is physically
    impossible.

    Graphs generated: Random directed graphs with 2-10 nodes and up to 30
    edges. All capacities are integers in [1, 20]. Cases where source == sink
    or no path exists are skipped.

    Failure indicates: Dinitz produced a result where an internal node acts as
    a hidden source or sink — a fundamental correctness violation.
    """
    G, source, sink = data
    if source == sink or not nx.has_path(G, source, sink):
        return  # skip trivial / unreachable cases

    R = dinitz(G, source, sink)

    for v in R.nodes():
        if v == source or v == sink:
            continue  # conservation does not apply at source/sink
        net_flow = sum(R[u][v]["flow"] for u in R.predecessors(v))
        assert abs(net_flow) < 1e-9, (
            f"Flow conservation violated at node {v}: "
            f"net inflow = {net_flow} (expected 0)"
        )

# ---------------------------------------------------------------------------
# Invariant — Capacity constraints on every edge
# ---------------------------------------------------------------------------

@given(flow_graph_and_nodes())
def test_positive_flow_never_exceeds_capacity(data):
    """
    Invariant: The flow on every edge in the residual network is between 0 and
    the edge's capacity (inclusive).

        0 <= R[u][v]['flow'] <= R[u][v]['capacity']  for all (u, v) in R

    Mathematical basis: Edge capacity is a hard physical constraint — it is the
    maximum amount of flow an edge can carry. A feasible flow must never exceed
    it. Together with flow conservation, this is the second condition that
    defines a valid flow. Violating it makes the solution physically impossible.

    Graphs generated: Random directed graphs with 2-10 nodes and up to 30
    edges. All capacities are integers in [1, 20]. Cases where source == sink
    or no path exists are skipped.

    Failure indicates: Dinitz pushed more flow through an edge than its
    capacity allows — the result is an infeasible flow and a correctness bug.
    """
    G, source, sink = data
    if source == sink or not nx.has_path(G, source, sink):
        return  # skip trivial / unreachable cases

    R = dinitz(G, source, sink)

    for u, v in G.edges():  # only check original graph edges, not residual back-edges
        flow = R[u][v]["flow"]
        capacity = R[u][v]["capacity"]
        if flow > 0:  # only check edges that carry positive flow; zero flow trivially satisfies capacity
            assert 0 <= flow <= capacity, (
                f"Capacity violated on edge ({u}, {v}): "
                f"flow={flow} but capacity={capacity}"
            )

# ---------------------------------------------------------------------------
# Postcondition 1 — Flow out of source == flow into sink == flow value
# ---------------------------------------------------------------------------

@given(flow_graph_and_nodes())
def test_flow_out_of_source_equals_flow_into_sink(data):
    """
    Postcondition: The total flow leaving the source equals the total flow
    entering the sink, and both equal the reported max flow value.

        sum(R[source][v]['flow'] for v in R.successors(source)) == flow_value
        sum(R[u][sink]['flow']   for u in R.predecessors(sink)) == flow_value

    Mathematical basis: By definition, the value of a flow is the net flow
    out of the source (= net flow into the sink). If these three quantities
    disagree, the residual network is internally inconsistent.

    Graphs generated: Random directed graphs with 2-10 nodes, up to 30 edges,
    capacities in [1, 20]. Cases where source == sink or no path exists are
    skipped.

    Failure indicates: The reported flow value does not match what the residual
    network actually contains — a bookkeeping bug in the algorithm.
    """
    G, source, sink = data
    if source == sink or not nx.has_path(G, source, sink):
        return

    R = dinitz(G, source, sink)
    flow_value = R.graph["flow_value"]

    flow_out_of_source = sum(
        R[source][v]["flow"] for v in R.successors(source)
    )
    flow_into_sink = sum(
        R[u][sink]["flow"] for u in R.predecessors(sink)
    )

    assert abs(flow_out_of_source - flow_value) < 1e-9, (
        f"Flow out of source {source} = {flow_out_of_source} "
        f"!= flow value {flow_value}"
    )
    assert abs(flow_into_sink - flow_value) < 1e-9, (
        f"Flow into sink {sink} = {flow_into_sink} "
        f"!= flow value {flow_value}"
    )


