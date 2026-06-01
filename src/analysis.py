
from __future__ import annotations
from collections import deque
from .graph import Graph


class LayerAnalyzer:


    def __init__(self, graph: Graph):
        self._graph = graph

    def compute_layers(self) -> list[list[str]]:
        in_degree: dict[str, int] = {n: 0 for n in self._graph.nodes()}
        for _, dst in self._graph.edges():
            in_degree[dst] += 1

        queue: deque[str] = deque(n for n, d in in_degree.items() if d == 0)
        layers: list[list[str]] = []

        while queue:
            current: list[str] = list(queue)
            queue.clear()
            layers.append(current)

            next_q: deque[str] = deque()
            for u in current:
                for v in self._graph.neighbors(u):
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        next_q.append(v)
            queue = next_q

        return layers

    def critical_path_length(self) -> int:
   
        return len(self.compute_layers())

    def parallelism_factor(self) -> float:
      
        layers = self.compute_layers()
        if not layers:
            return 0.0
        return round(self._graph.num_nodes / len(layers), 2)


class GraphMetrics:


    def __init__(self, graph: Graph):
        self._g = graph

    def density(self) -> float:
        v = self._g.num_nodes
        if v <= 1:
            return 0.0
        return round(self._g.num_edges / (v * (v - 1)), 6)

    def out_degree_stats(self) -> dict:
        degrees = [len(self._g.neighbors(n)) for n in self._g.nodes()]
        if not degrees:
            return {}
        avg = sum(degrees) / len(degrees)
        max_d = max(degrees)
        hub = max(self._g.nodes(), key=lambda n: len(self._g.neighbors(n)))
        return {"avg": round(avg, 2), "max": max_d, "hub": hub}

    def source_nodes(self) -> list[str]:

        has_pred = {dst for _, dst in self._g.edges()}
        return [n for n in self._g.nodes() if n not in has_pred]

    def sink_nodes(self) -> list[str]:
     
        return [n for n in self._g.nodes() if not self._g.neighbors(n)]
