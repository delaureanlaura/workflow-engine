"""
RF02 — Ordenação Topológica (Kahn's Algorithm — BFS)
RF03 — Detecção de Ciclos via DFS (coloração tricolor)

Complexidade: O(V + E) para ambos os algoritmos.
"""

from collections import deque
from .graph import Graph


# ══════════════════════════════════════════════════════════════════════ #
#  RF03 — Detecção de Ciclos (DFS com 3 cores)
# ══════════════════════════════════════════════════════════════════════ #

_WHITE = 0   # Não visitado
_GRAY  = 1   # Em processamento (na pilha de chamadas)
_BLACK = 2   # Totalmente processado


class CycleDetector:
    """
    Detecta ciclos em um grafo direcionado usando DFS com coloração tricolor.

    Um nó GRAY na pilha de recursão indica back-edge → ciclo presente.
    Complexidade: O(V + E)
    """

    def __init__(self, graph: Graph):
        self._graph = graph
        self._color: dict[str, int] = {}
        self._cycle_path: list[str] = []
        self._parent: dict[str, str | None] = {}

    def has_cycle(self) -> bool:
        """Retorna True se existir ao menos um ciclo."""
        self._color = {n: _WHITE for n in self._graph.nodes()}
        self._parent = {n: None for n in self._graph.nodes()}
        self._cycle_path = []

        for node in self._graph.nodes():
            if self._color[node] == _WHITE:
                if self._dfs_visit(node):
                    return True
        return False

    def _dfs_visit(self, u: str) -> bool:
        """DFS iterativa para evitar stack overflow em grafos grandes."""
        stack = [(u, iter(self._graph.neighbors(u)))]
        self._color[u] = _GRAY

        while stack:
            node, children = stack[-1]
            try:
                child = next(children)
                if self._color[child] == _GRAY:
                    # Back-edge encontrado → ciclo!
                    self._reconstruct_cycle(child, node)
                    return True
                if self._color[child] == _WHITE:
                    self._color[child] = _GRAY
                    self._parent[child] = node
                    stack.append((child, iter(self._graph.neighbors(child))))
            except StopIteration:
                self._color[node] = _BLACK
                stack.pop()

        return False

    def _reconstruct_cycle(self, cycle_start: str, cycle_end: str) -> None:
        """Reconstrói o caminho do ciclo para diagnóstico."""
        path = [cycle_end, cycle_start]
        cur = cycle_start
        while cur != cycle_end and self._parent.get(cur):
            cur = self._parent[cur]
            path.append(cur)
        self._cycle_path = list(reversed(path))

    @property
    def cycle_path(self) -> list[str]:
        return self._cycle_path


# ══════════════════════════════════════════════════════════════════════ #
#  RF02 — Ordenação Topológica (Algoritmo de Kahn — BFS)
# ══════════════════════════════════════════════════════════════════════ #


class TopologicalSort:
    """
    Ordenação topológica pelo Algoritmo de Kahn.

    Etapas:
      1. Calcula in-degree de cada nó.
      2. Enfileira nós com in-degree == 0 (sem dependências).
      3. Processa a fila: ao remover u, reduz in-degree dos vizinhos;
         vizinhos que chegam a 0 são enfileirados.
      4. Se todos os nós foram processados → grafo é acíclico.

    Complexidade: O(V + E)
    """

    def __init__(self, graph: Graph):
        self._graph = graph

    def sort(self) -> list[str]:
        """
        Retorna a lista ordenada de tarefas a executar.
        Lança ValueError se o grafo contiver ciclo.
        """
        in_degree: dict[str, int] = {n: 0 for n in self._graph.nodes()}

        # Calcula in-degree de cada nó — O(V + E)
        for src, dst in self._graph.edges():
            in_degree[dst] += 1

        # Fila com todos os nós sem predecessores
        queue: deque[str] = deque()
        for node, deg in in_degree.items():
            if deg == 0:
                queue.append(node)

        order: list[str] = []

        while queue:
            u = queue.popleft()
            order.append(u)

            for v in self._graph.neighbors(u):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(order) != self._graph.num_nodes:
            raise ValueError(
                "Ciclo detectado: ordenação topológica impossível. "
                "Execute CycleDetector.has_cycle() para identificar o deadlock."
            )

        return order
