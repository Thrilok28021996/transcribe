"""Knowledge Graph database store for tracking meeting entities and relationships."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)


class GraphNode(BaseModel):
    """Entity node in the knowledge graph."""
    model_config = ConfigDict(frozen=True)

    id: str
    label: str  # e.g., "Person", "Meeting", "Task", "Decision", "Project", "Technology"
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Directed edge / relationship in the knowledge graph."""
    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    relation_type: str  # e.g., "owns", "uses", "depends_on", "discusses", "assigned_to"
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphStore:
    """Persistent knowledge graph database for entities and typed relationships."""

    def __init__(self, storage_dir: Path | str) -> None:
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.storage_dir / "graph.json"
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._load()

    def _load(self) -> None:
        """Load knowledge graph state from disk."""
        if not self.db_file.is_file():
            return

        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("nodes", []):
                    node = GraphNode.model_validate(item)
                    self._nodes[node.id] = node
                for item in data.get("edges", []):
                    edge = GraphEdge.model_validate(item)
                    self._edges.append(edge)
            logger.info(f"Loaded {len(self._nodes)} nodes and {len(self._edges)} edges from graph.json")
        except (json.JSONDecodeError, OSError) as err:
            logger.error(f"Failed to load knowledge graph: {err}. Initializing empty graph.")
            self._nodes = {}
            self._edges = []

    def _save(self) -> None:
        """Persist knowledge graph state to disk."""
        try:
            serialized = {
                "nodes": [n.model_dump(mode="json") for n in self._nodes.values()],
                "edges": [e.model_dump(mode="json") for e in self._edges],
            }
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
        except OSError as err:
            logger.error(f"Failed to save knowledge graph: {err}")

    def add_node(self, node: GraphNode) -> GraphNode:
        """Add or update an entity node."""
        self._nodes[node.id] = node
        self._save()
        return node

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        """Add a typed edge between two nodes."""
        # Avoid exact duplicate edges
        for existing in self._edges:
            if (
                existing.source_id == edge.source_id
                and existing.target_id == edge.target_id
                and existing.relation_type == edge.relation_type
            ):
                return existing

        self._edges.append(edge)
        self._save()
        return edge

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve node by ID."""
        return self._nodes.get(node_id)

    def find_nodes_by_label(self, label: str) -> list[GraphNode]:
        """Find all nodes matching a specific entity label."""
        label_clean = label.strip().lower()
        return [n for n in self._nodes.values() if n.label.lower() == label_clean]

    def query_neighbors(self, node_id: str) -> list[tuple[GraphNode, GraphEdge, GraphNode]]:
        """Query 1-hop outgoing and incoming relationships for a node."""
        results: list[tuple[GraphNode, GraphEdge, GraphNode]] = []
        for edge in self._edges:
            if edge.source_id == node_id:
                target = self.get_node(edge.target_id)
                source = self.get_node(node_id)
                if source and target:
                    results.append((source, edge, target))
            elif edge.target_id == node_id:
                source = self.get_node(edge.source_id)
                target = self.get_node(node_id)
                if source and target:
                    results.append((source, edge, target))
        return results

    def stats(self) -> dict[str, int]:
        """Summary metrics for graph nodes and edges."""
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
        }

    def clear(self) -> None:
        """Clear all graph nodes and edges and delete persistence file."""
        self._nodes.clear()
        self._edges.clear()
        if self.db_file.exists():
            try:
                self.db_file.unlink()
            except OSError:
                pass

