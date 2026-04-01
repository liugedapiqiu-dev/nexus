#!/usr/bin/env python3
"""Workflow DAG Graph Builder (v0.2 foundation)

Builds dependency graph from workflow steps and provides:
- reverse edges
- roots
- topological sort (cycle detection)
- ready-step computation given a completed set

Steps can be either:
- dict objects from workflow files: {"id": str, "depends_on": [str], ...}
- PlanStep dataclass instances with attributes: id, depends_on
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set


class WorkflowCycleError(ValueError):
    pass


def _step_id(step: Any) -> str:
    if isinstance(step, dict):
        sid = step.get("id")
    else:
        sid = getattr(step, "id", None)
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError(f"Step missing valid id: {step}")
    return sid


def _step_deps(step: Any) -> List[str]:
    if isinstance(step, dict):
        deps = step.get("depends_on", [])
    else:
        deps = getattr(step, "depends_on", [])
    if deps is None:
        return []
    if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
        raise ValueError(f"depends_on must be list[str] for step: {_step_id(step)}")
    return deps


@dataclass
class WorkflowGraph:
    """DAG graph for a workflow."""

    nodes: Dict[str, Any]
    deps: Dict[str, Set[str]]
    reverse: Dict[str, Set[str]]

    @classmethod
    def from_steps(cls, steps: Iterable[Any]) -> "WorkflowGraph":
        steps = list(steps)
        nodes: Dict[str, Any] = {}
        deps: Dict[str, Set[str]] = {}
        reverse: Dict[str, Set[str]] = {}

        for s in steps:
            sid = _step_id(s)
            if sid in nodes:
                raise ValueError(f"Duplicate step id: {sid}")
            nodes[sid] = s
            deps[sid] = set(_step_deps(s))
            reverse[sid] = set()

        # Build reverse edges + validate deps exist
        for sid, dset in deps.items():
            if sid in dset:
                raise ValueError(f"Step '{sid}' cannot depend on itself")
            for d in dset:
                if d not in nodes:
                    raise ValueError(f"Step '{sid}' depends on unknown step '{d}'")
                reverse[d].add(sid)

        return cls(nodes=nodes, deps=deps, reverse=reverse)

    def roots(self) -> List[str]:
        return [sid for sid, d in self.deps.items() if len(d) == 0]

    def topological_sort(self) -> List[str]:
        """Kahn topological sort. Raises WorkflowCycleError if cycle detected."""
        in_degree = {sid: len(d) for sid, d in self.deps.items()}
        q = deque([sid for sid, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while q:
            sid = q.popleft()
            order.append(sid)
            for child in self.reverse.get(sid, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    q.append(child)

        if len(order) != len(self.nodes):
            raise WorkflowCycleError("Workflow DAG cycle detected")

        return order

    def get_ready(self, completed: Set[str]) -> List[str]:
        ready: List[str] = []
        for sid, dset in self.deps.items():
            if sid in completed:
                continue
            if dset.issubset(completed):
                ready.append(sid)
        return ready
