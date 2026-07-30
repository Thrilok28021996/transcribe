"""Unit tests for KnowledgeGraphStore."""

from pathlib import Path
from transcribe.infrastructure.graph_store import GraphEdge, GraphNode, KnowledgeGraphStore


def test_graph_store_nodes_and_edges(tmp_path: Path) -> None:
    graph = KnowledgeGraphStore(storage_dir=tmp_path)
    assert graph.stats()["total_nodes"] == 0

    alice = GraphNode(id="Alice", label="Person", properties={"role": "Engineer"})
    python_tech = GraphNode(id="Python", label="Technology", properties={"category": "Language"})

    graph.add_node(alice)
    graph.add_node(python_tech)

    edge = GraphEdge(source_id="Alice", target_id="Python", relation_type="uses", confidence=0.98)
    graph.add_edge(edge)

    assert graph.stats()["total_nodes"] == 2
    assert graph.stats()["total_edges"] == 1

    neighbors = graph.query_neighbors("Alice")
    assert len(neighbors) == 1
    src, rel, tgt = neighbors[0]
    assert src.id == "Alice"
    assert tgt.id == "Python"
    assert rel.relation_type == "uses"
