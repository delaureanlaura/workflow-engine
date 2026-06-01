"""
RF04 — Fila de Prioridade (Max-Heap)

Implementação manual de um Max-Heap binário.
Complexidade:
  - insert:    O(log N)
  - extract_max: O(log N)
  - peek:      O(1)
  - build:     O(N)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class Task:
    """
    Representa uma tarefa pronta para execução.
    A comparação é baseada apenas na prioridade (urgência).
    """
    priority: int                          # Maior = mais urgente
    task_id: str   = field(compare=False)
    metadata: dict = field(compare=False, default_factory=dict)

    def __repr__(self) -> str:
        return f"Task(id={self.task_id!r}, priority={self.priority})"


class MaxHeap:
    """
    Max-Heap binário sobre lista contígua.

    Invariante: heap[i] >= heap[2i+1] e heap[i] >= heap[2i+2]

    Indexação (base-0):
      pai(i)         = (i - 1) // 2
      filho_esq(i)   = 2*i + 1
      filho_dir(i)   = 2*i + 2
    """

    def __init__(self):
        self._data: list[Task] = []

    # ------------------------------------------------------------------ #
    #  Helpers de índice
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parent(i: int) -> int:
        return (i - 1) // 2

    @staticmethod
    def _left(i: int) -> int:
        return 2 * i + 1

    @staticmethod
    def _right(i: int) -> int:
        return 2 * i + 2

    # ------------------------------------------------------------------ #
    #  Operações de manutenção da invariante
    # ------------------------------------------------------------------ #

    def _sift_up(self, i: int) -> None:
        """Sobe o elemento na posição i até restaurar a invariante. O(log N)"""
        while i > 0:
            p = self._parent(i)
            if self._data[i] > self._data[p]:
                self._data[i], self._data[p] = self._data[p], self._data[i]
                i = p
            else:
                break

    def _sift_down(self, i: int) -> None:
        """Desce o elemento na posição i até restaurar a invariante. O(log N)"""
        n = len(self._data)
        while True:
            largest = i
            left  = self._left(i)
            right = self._right(i)

            if left < n and self._data[left] > self._data[largest]:
                largest = left
            if right < n and self._data[right] > self._data[largest]:
                largest = right

            if largest == i:
                break

            self._data[i], self._data[largest] = self._data[largest], self._data[i]
            i = largest

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def insert(self, task: Task) -> None:
        """Insere uma tarefa na heap. O(log N)"""
        self._data.append(task)
        self._sift_up(len(self._data) - 1)

    def extract_max(self) -> Task:
        """Remove e retorna a tarefa de maior prioridade. O(log N)"""
        if not self._data:
            raise IndexError("Heap vazia: nenhuma tarefa disponível.")

        # Troca raiz com o último elemento e remove
        self._data[0], self._data[-1] = self._data[-1], self._data[0]
        max_task = self._data.pop()
        if self._data:
            self._sift_down(0)
        return max_task

    def peek(self) -> Task:
        """Retorna a tarefa de maior prioridade sem remover. O(1)"""
        if not self._data:
            raise IndexError("Heap vazia.")
        return self._data[0]

    def build_from(self, tasks: list[Task]) -> None:
        """
        Constrói a heap a partir de uma lista já existente.
        Algoritmo de Floyd — O(N), mais eficiente que N inserções.
        """
        self._data = list(tasks)
        # Começa do último nó interno e desce todos
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(i)

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __repr__(self) -> str:
        top = self._data[0] if self._data else None
        return f"MaxHeap(size={len(self)}, top={top})"
