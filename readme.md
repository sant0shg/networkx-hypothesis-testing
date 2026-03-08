# Property-Based Testing for NetworkX

A collection of property-based tests for [NetworkX](https://networkx.org/documentation/stable/) graph algorithms, written with the [Hypothesis](https://hypothesis.readthedocs.io/) library.

## What We're Building

NetworkX has solid unit test coverage with pytest, but no property-based tests. We're adding them.

Instead of hand-crafted examples, Hypothesis automatically generates hundreds of diverse graph inputs and checks that algorithm outputs always satisfy mathematical invariants. This surfaces edge cases that example-based tests miss.

## Algorithms Under Test

| Algorithm | NetworkX function | Properties tested |
|---|---|---|
| **Dijkstra's Shortest Path** | `single_source_dijkstra_path_length` | Self-distance is 0, all distances non-negative |

## Properties We Test

Each test verifies a fundamental property of the algorithm:

| Property Type | Description | Example |
|---|---|---|
| **Invariants** | Always hold | Shortest path A→B ≤ any other path A→B |
| **Postconditions** | Expected output shape | Spanning tree has exactly n−1 edges |
| **Metamorphic** | Output relationships on transformed inputs | Reversing all edges reverses shortest paths |
| **Idempotence** | Applying twice = applying once | — |
| **Boundary conditions** | Edge cases | Empty graphs, single nodes, disconnected components |

## Getting Started

### 1. Clone and set up

```bash
git clone <repo-url>
cd networkx
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run all tests

```bash
pytest tests/ -v
```

### 3. Run a specific test file

```bash
pytest main.py -v
```

### 4. Run a single test

```bash
pytest main.py::test_self_distance_is_zero -v
```

### 5. See Hypothesis examples as they're generated

```bash
pytest tests/ -v -s
```

The `-s` flag disables output capturing so you can see `print()` statements inside tests — useful for inspecting what graphs Hypothesis is generating.

## Structure

```
main.py            # all property-based tests
requirements.txt   # project dependencies
docs/              # project brief
```

`main.py` contains:
- Custom Hypothesis strategies for generating weighted graphs
- Invariant tests for **Dijkstra's shortest path** (`single_source_dijkstra_path_length`)
- Tests decorated with `@given(...)` with docstrings explaining each property, its mathematical basis, and what a failure means

## Resources

- [Hypothesis docs](https://hypothesis.readthedocs.io/)
- [NetworkX docs](https://networkx.org/documentation/stable/)
