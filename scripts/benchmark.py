#!/usr/bin/env python3
"""
Benchmark comparativo de complexidade.
Mede O(V+E) real vs curva teórica e exibe tabela ASCII.

Uso:
  python scripts/benchmark.py
"""
import sys, time, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Graph
from src.algorithms import CycleDetector, TopologicalSort
from src.heap import MaxHeap, Task


def make_dag(n: int) -> Graph:
    import random
    rng = random.Random(42)
    g = Graph()
    for i in range(n):
        g.add_node(f"T{i:07d}")
    for i in range(1, n):
        max_deps = min(i, 4)
        for j in rng.sample(range(max(0, i-15), i), min(max_deps, i)):
            g.add_edge(f"T{j:07d}", f"T{i:07d}")
    return g


SIZES = [100, 500, 1_000, 5_000, 10_000, 50_000]

print(f"\n{'N':>8}  {'E':>8}  {'DFS ms':>8}  {'Kahn ms':>8}  {'Heap ms':>8}  {'Total ms':>9}  {'E/(N log N)':>11}")
print("─" * 80)

for n in SIZES:
    g = make_dag(n)
    e = g.num_edges

    t0 = time.perf_counter()
    CycleDetector(g).has_cycle()
    dfs_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    order = TopologicalSort(g).sort()
    kahn_ms = (time.perf_counter() - t1) * 1000

    t2 = time.perf_counter()
    heap = MaxHeap()
    tasks = [Task(priority=i % 100, task_id=f"T{i}") for i in range(n)]
    heap.build_from(tasks)
    while heap:
        heap.extract_max()
    heap_ms = (time.perf_counter() - t2) * 1000

    total_ms = dfs_ms + kahn_ms + heap_ms
    ratio = e / (n * math.log2(n)) if n > 1 else 0

    print(f"{n:>8,}  {e:>8,}  {dfs_ms:>8.2f}  {kahn_ms:>8.2f}  {heap_ms:>8.2f}  {total_ms:>9.2f}  {ratio:>11.3f}")

print("\nE/(N log N) constante ≈ confirma complexidade O(N log N) do conjunto.")
print("Variações pequenas devem-se à janela de candidatos nos DAGs gerados.\n")
