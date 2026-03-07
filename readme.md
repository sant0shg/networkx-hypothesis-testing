# Property-Based Testing for NetworkX

A collection of property-based tests for [NetworkX](https://networkx.org/documentation/stable/) graph algorithms, written with the [Hypothesis](https://hypothesis.readthedocs.io/) library.

## What We're Building

NetworkX has solid unit test coverage with pytest, but no property-based tests. We're adding them.

Instead of hand-crafted examples, Hypothesis automatically generates hundreds of diverse graph inputs and checks that algorithm outputs always satisfy mathematical invariants. This surfaces edge cases that example-based tests miss.

## Algorithms Under Test

We're targeting graph analytics algorithms from NetworkX, including areas like:

- Shortest paths
- Centrality measures
- Spanning trees
- Connectivity
- Matching and flow algorithms
- Community detection

## Properties We Test

Each test verifies a fundamental property of the algorithm:

| Property Type | Description | Example |
|---|---|---|
| **Invariants** | Always hold | Shortest path A→B ≤ any other path A→B |
| **Postconditions** | Expected output shape | Spanning tree has exactly n−1 edges |
| **Metamorphic** | Output relationships on transformed inputs | Reversing all edges reverses shortest paths |
| **Idempotence** | Applying twice = applying once | — |
| **Boundary conditions** | Edge cases | Empty graphs, single nodes, disconnected components |

## Setup

```bash
git clone <repo-url>
cd networkx
python -m venv .venv && source .venv/bin/activate
pip install networkx hypothesis pytest
```

## Running Tests

```bash
pytest tests/ -v
```

## Structure

```
tests/
  test_<algorithm>.py   # property-based tests with Hypothesis
```

Each test file includes:
- Custom Hypothesis strategies for generating graphs
- Tests decorated with `@given(...)` covering the properties above
- Docstrings explaining the property, its mathematical basis, and what a failure means

## Resources

- [Hypothesis docs](https://hypothesis.readthedocs.io/)
- [NetworkX docs](https://networkx.org/documentation/stable/)
