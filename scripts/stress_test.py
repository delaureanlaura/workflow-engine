#!/usr/bin/env python3
"""
Teste de Carga — Prova de que o sistema suporta volume massivo.

Executa os 3 cenários e mede:
  - Tempo de execução (ms)
  - Pico de memória (MB)
  - Throughput (tarefas/segundo)

Uso:
  python scripts/stress_test.py
"""

import json
import sys
import time
import tracemalloc
from pathlib import Path

# Adiciona o diretório raiz ao path para importar src/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.engine import WorkflowEngine

DATA_DIR = ROOT / "data"

SCENARIOS = [
    ("Básico",   DATA_DIR / "basico.json"),
    ("Avançado", DATA_DIR / "avancado.json"),
    ("Estresse", DATA_DIR / "estresse.json"),
]

SEP = "─" * 72


def run_scenario(label: str, path: Path) -> None:
    print(f"\n{'═' * 72}")
    print(f"  CENÁRIO: {label}  ({path.name})")
    print(SEP)

    if not path.exists():
        print(f"  [ERRO] Arquivo não encontrado. Execute: python scripts/generate_data.py")
        return

    # Carrega JSON
    t0 = time.perf_counter()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    load_ms = (time.perf_counter() - t0) * 1000

    num_tasks = len(data["tasks"])
    num_edges = sum(len(t.get("dependencies", [])) for t in data["tasks"])

    print(f"  Tarefas : {num_tasks:>8,}")
    print(f"  Arestas : {num_edges:>8,}")
    print(f"  Leitura : {load_ms:>8.1f} ms")
    print(SEP)

    # Medição de memória
    tracemalloc.start()
    engine = WorkflowEngine()
    engine.load_from_dict(data)

    # Detecção de ciclos
    t1 = time.perf_counter()
    try:
        engine.check_deadlocks()
        cycle_ms = (time.perf_counter() - t1) * 1000
        print(f"  RF03 DFS (ciclos)       : {cycle_ms:>8.2f} ms  → SEM CICLO ✓")
    except RuntimeError as e:
        cycle_ms = (time.perf_counter() - t1) * 1000
        print(f"  RF03 DFS (ciclos)       : {cycle_ms:>8.2f} ms  → CICLO DETECTADO ✗")
        tracemalloc.stop()
        return

    # Ordenação topológica
    t2 = time.perf_counter()
    order = engine.topological_order()
    topo_ms = (time.perf_counter() - t2) * 1000
    print(f"  RF02 Ordenação Topológica: {topo_ms:>8.2f} ms")

    # Heap de prioridade
    t3 = time.perf_counter()
    engine.build_ready_queue(order)
    heap_ms = (time.perf_counter() - t3) * 1000
    print(f"  RF04 Build Max-Heap      : {heap_ms:>8.2f} ms")

    # Drenagem completa da heap
    t4 = time.perf_counter()
    count = 0
    while engine.heap:
        engine.heap.extract_max()
        count += 1
    drain_ms = (time.perf_counter() - t4) * 1000
    print(f"  RF04 Drain Heap ({count:,})  : {drain_ms:>8.2f} ms")

    # Totais
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / (1024 * 1024)

    total_ms = cycle_ms + topo_ms + heap_ms + drain_ms
    throughput = num_tasks / (total_ms / 1000) if total_ms > 0 else float("inf")

    print(SEP)
    print(f"  TOTAL (sem I/O)          : {total_ms:>8.2f} ms")
    print(f"  Pico de memória          : {peak_mb:>8.2f} MB")
    print(f"  Throughput               : {throughput:>8,.0f} tarefas/s")


def run_cycle_scenario(label: str, path: Path) -> None:
    """Testa o cenário COM ciclo para validar RF03."""
    if not path.exists():
        return

    print(f"\n  [RF03] Testando detecção de deadlock em '{path.name}'...")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    engine = WorkflowEngine()
    engine.load_from_dict(data)

    t0 = time.perf_counter()
    try:
        engine.check_deadlocks()
        print(f"  [✗] FALHOU — ciclo não detectado!")
    except RuntimeError as e:
        ms = (time.perf_counter() - t0) * 1000
        print(f"  [✓] Ciclo detectado em {ms:.2f} ms → Execução abortada corretamente.")


def main() -> None:
    print("\n" + "═" * 72)
    print("  WORKFLOW ENGINE — PROVA DE CARGA")
    print("═" * 72)

    for label, path in SCENARIOS:
        run_scenario(label, path)

    # Testa detecção de ciclos nos 3 cenários
    print(f"\n{'═' * 72}")
    print("  VALIDAÇÃO RF03 — Detecção de Deadlocks")
    print(SEP)
    for label, path in SCENARIOS:
        cycle_path = path.parent / path.name.replace(".json", "_ciclo.json")
        run_cycle_scenario(label, cycle_path)

    print(f"\n{'═' * 72}\n")


if __name__ == "__main__":
    main()
