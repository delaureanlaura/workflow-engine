import json
import time
from pathlib import Path

from .graph import Graph
from .algorithms import CycleDetector, TopologicalSort
from .heap import MaxHeap, Task


class WorkflowEngine:


    def __init__(self):
        self.graph    = Graph()
        self.heap     = MaxHeap()
        self._results: list[dict] = []

    # ------------------------------------------------------------------ #
    #  Carga de dados
    # ------------------------------------------------------------------ #

    def load_from_file(self, path: str | Path) -> None:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._build_graph(data)

    def load_from_dict(self, data: dict) -> None:
        self._build_graph(data)

    def _build_graph(self, data: dict) -> None:

        self.graph = Graph()

        tasks = data.get("tasks", [])
        for task in tasks:
            tid = task["id"]
            metadata = {
                "name":     task.get("name", tid),
                "priority": task.get("priority", 1),
                "duration": task.get("duration_ms", 0),
            }
            self.graph.add_node(tid, metadata)

        for task in tasks:
            tid = task["id"]
            for dep in task.get("dependencies", []):
                # dep → tid significa: dep deve rodar antes de tid
                self.graph.add_edge(dep, tid)

    # ------------------------------------------------------------------ #
    #  Etapa 1 — Detecção de ciclos (RF03)
    # ------------------------------------------------------------------ #

    def check_deadlocks(self) -> bool:
   
        detector = CycleDetector(self.graph)
        if detector.has_cycle():
            path_str = " → ".join(detector.cycle_path) if detector.cycle_path else "desconhecido"
            raise RuntimeError(
                f"DEADLOCK DETECTADO! Ciclo encontrado no caminho: {path_str}\n"
                "Execução abortada preventivamente."
            )
        return True

    # ------------------------------------------------------------------ #
    #  Etapa 2 — Ordenação topológica (RF02)
    # ------------------------------------------------------------------ #

    def topological_order(self) -> list[str]:
   
        sorter = TopologicalSort(self.graph)
        return sorter.sort()

    # ------------------------------------------------------------------ #
    #  Etapa 3 — Alocação por prioridade (RF04)
    # ------------------------------------------------------------------ #

    def build_ready_queue(self, order: list[str]) -> None:
  
        self.heap = MaxHeap()
        tasks_for_heap: list[Task] = []

        for tid in order:
            meta = self.graph.get_metadata(tid)
            t = Task(
                priority=meta.get("priority", 1),
                task_id=tid,
                metadata=meta,
            )
            tasks_for_heap.append(t)

        # Usa Floyd build — O(N) em vez de N × O(log N)
        self.heap.build_from(tasks_for_heap)

    # ------------------------------------------------------------------ #
    #  Execução completa
    # ------------------------------------------------------------------ #

    def run(self) -> dict:
    
        start_time = time.perf_counter()

        # RF03 — Verificação de ciclos
        self.check_deadlocks()

        # RF02 — Ordem de execução
        order = self.topological_order()

        # RF04 — Heap de prioridade
        self.build_ready_queue(order)

        # Simula execução drenando a heap
        execution_log: list[dict] = []
        step = 1
        while self.heap:
            task = self.heap.extract_max()
            execution_log.append({
                "step":     step,
                "task_id":  task.task_id,
                "name":     task.metadata.get("name", task.task_id),
                "priority": task.priority,
            })
            step += 1

        elapsed = time.perf_counter() - start_time

        return {
            "status":          "success",
            "total_tasks":     self.graph.num_nodes,
            "total_edges":     self.graph.num_edges,
            "elapsed_ms":      round(elapsed * 1000, 3),
            "execution_order": execution_log,
        }
