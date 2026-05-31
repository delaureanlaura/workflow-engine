"""
RF01 — Grafo Direcionado com Lista de Adjacência
Implementação manual, sem bibliotecas de grafos externas.
"""


class Graph:
    """
    Grafo Direcionado representado por Lista de Adjacência.
    Complexidade de espaço: O(V + E)
    """

    def __init__(self):
        # Dicionário: chave = id da tarefa, valor = lista de vizinhos (dependentes)
        self._adjacency: dict[str, list[str]] = {}
        # Armazena metadados das tarefas
        self._nodes: dict[str, dict] = {}

    # ------------------------------------------------------------------ #
    #  Operações básicas
    # ------------------------------------------------------------------ #

    def add_node(self, task_id: str, metadata: dict | None = None) -> None:
        """Adiciona um nó (tarefa) ao grafo. O(1)"""
        if task_id not in self._adjacency:
            self._adjacency[task_id] = []
            self._nodes[task_id] = metadata or {}

    def add_edge(self, from_id: str, to_id: str) -> None:
        """
        Adiciona aresta direcionada from_id → to_id,
        significando que from_id deve ser executado ANTES de to_id.
        O(1) amortizado.
        """
        if from_id not in self._adjacency:
            self.add_node(from_id)
        if to_id not in self._adjacency:
            self.add_node(to_id)
        self._adjacency[from_id].append(to_id)

    def neighbors(self, task_id: str) -> list[str]:
        """Retorna os vizinhos (dependentes) de um nó. O(1)"""
        return self._adjacency.get(task_id, [])

    def get_metadata(self, task_id: str) -> dict:
        """Retorna os metadados de uma tarefa."""
        return self._nodes.get(task_id, {})

    def nodes(self) -> list[str]:
        """Retorna todos os nós do grafo."""
        return list(self._adjacency.keys())

    def edges(self) -> list[tuple[str, str]]:
        """Retorna todas as arestas do grafo."""
        result = []
        for src, dests in self._adjacency.items():
            for dst in dests:
                result.append((src, dst))
        return result

    @property
    def num_nodes(self) -> int:
        return len(self._adjacency)

    @property
    def num_edges(self) -> int:
        return sum(len(v) for v in self._adjacency.values())

    def __repr__(self) -> str:
        return (
            f"Graph(nodes={self.num_nodes}, edges={self.num_edges})"
        )
