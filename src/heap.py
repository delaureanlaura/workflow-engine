
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class Task:

    priority: int                          # Maior = mais urgente
    task_id: str   = field(compare=False)
    metadata: dict = field(compare=False, default_factory=dict)

    def __repr__(self) -> str:
        return f"Task(id={self.task_id!r}, priority={self.priority})"


class MaxHeap:

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

        while i > 0:
            p = self._parent(i)
            if self._data[i] > self._data[p]:
                self._data[i], self._data[p] = self._data[p], self._data[i]
                i = p
            else:
                break

    def _sift_down(self, i: int) -> None:

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

        self._data.append(task)
        self._sift_up(len(self._data) - 1)

    def extract_max(self) -> Task:

        if not self._data:
            raise IndexError("Heap vazia: nenhuma tarefa disponível.")

        # Troca raiz com o último elemento e remove
        self._data[0], self._data[-1] = self._data[-1], self._data[0]
        max_task = self._data.pop()
        if self._data:
            self._sift_down(0)
        return max_task

    def peek(self) -> Task:
        if not self._data:
            raise IndexError("Heap vazia.")
        return self._data[0]

    def build_from(self, tasks: list[Task]) -> None:

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
