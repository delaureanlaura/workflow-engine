#!/usr/bin/env python3
"""
Testes Unitários — Workflow Engine
Cobre RF01, RF02, RF03 e RF04.

Uso:
  python -m pytest tests/test_engine.py -v
  # ou sem pytest:
  python tests/test_engine.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Graph
from src.heap import MaxHeap, Task
from src.algorithms import CycleDetector, TopologicalSort
from src.engine import WorkflowEngine


# ══════════════════════════════════════════════════════════════════════ #
#  RF01 — Grafo
# ══════════════════════════════════════════════════════════════════════ #

def test_graph_add_node():
    g = Graph()
    g.add_node("A", {"name": "Agente A"})
    assert "A" in g.nodes()
    assert g.num_nodes == 1

def test_graph_add_edge():
    g = Graph()
    g.add_edge("A", "B")
    assert "B" in g.neighbors("A")
    assert g.num_edges == 1

def test_graph_multiple_neighbors():
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    assert set(g.neighbors("A")) == {"B", "C"}


# ══════════════════════════════════════════════════════════════════════ #
#  RF03 — Detecção de Ciclos
# ══════════════════════════════════════════════════════════════════════ #

def test_no_cycle():
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    detector = CycleDetector(g)
    assert detector.has_cycle() is False

def test_simple_cycle():
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")  # Ciclo!
    detector = CycleDetector(g)
    assert detector.has_cycle() is True

def test_self_loop():
    g = Graph()
    g.add_edge("A", "A")  # Auto-loop
    detector = CycleDetector(g)
    assert detector.has_cycle() is True

def test_diamond_no_cycle():
    g = Graph()
    #   A
    #  / \
    # B   C
    #  \ /
    #   D
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "D")
    g.add_edge("C", "D")
    detector = CycleDetector(g)
    assert detector.has_cycle() is False


# ══════════════════════════════════════════════════════════════════════ #
#  RF02 — Ordenação Topológica
# ══════════════════════════════════════════════════════════════════════ #

def test_topo_linear_chain():
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    order = TopologicalSort(g).sort()
    # A deve vir antes de B, B antes de C
    assert order.index("A") < order.index("B") < order.index("C")

def test_topo_raises_on_cycle():
    g = Graph()
    g.add_edge("X", "Y")
    g.add_edge("Y", "X")
    try:
        TopologicalSort(g).sort()
        assert False, "Deveria ter levantado ValueError"
    except ValueError:
        pass

def test_topo_diamond():
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "D")
    g.add_edge("C", "D")
    order = TopologicalSort(g).sort()
    assert order.index("A") < order.index("D")
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")


# ══════════════════════════════════════════════════════════════════════ #
#  RF04 — Max-Heap
# ══════════════════════════════════════════════════════════════════════ #

def test_heap_max_order():
    heap = MaxHeap()
    heap.insert(Task(priority=3, task_id="T3"))
    heap.insert(Task(priority=1, task_id="T1"))
    heap.insert(Task(priority=5, task_id="T5"))
    heap.insert(Task(priority=2, task_id="T2"))

    assert heap.extract_max().priority == 5
    assert heap.extract_max().priority == 3
    assert heap.extract_max().priority == 2
    assert heap.extract_max().priority == 1

def test_heap_peek_no_remove():
    heap = MaxHeap()
    heap.insert(Task(priority=10, task_id="X"))
    assert heap.peek().priority == 10
    assert len(heap) == 1  # Não removeu

def test_heap_empty_raises():
    heap = MaxHeap()
    try:
        heap.extract_max()
        assert False, "Deveria ter levantado IndexError"
    except IndexError:
        pass

def test_heap_build_from():
    tasks = [Task(priority=i, task_id=f"T{i}") for i in [4, 7, 2, 9, 1]]
    heap = MaxHeap()
    heap.build_from(tasks)
    assert heap.extract_max().priority == 9
    assert heap.extract_max().priority == 7


# ══════════════════════════════════════════════════════════════════════ #
#  Integração — Engine completo
# ══════════════════════════════════════════════════════════════════════ #

def test_engine_full_run():
    data = {
        "tasks": [
            {"id": "T1", "name": "Init",    "priority": 10, "dependencies": []},
            {"id": "T2", "name": "Fetch",   "priority": 5,  "dependencies": ["T1"]},
            {"id": "T3", "name": "Process", "priority": 8,  "dependencies": ["T1"]},
            {"id": "T4", "name": "Save",    "priority": 3,  "dependencies": ["T2", "T3"]},
        ]
    }
    engine = WorkflowEngine()
    engine.load_from_dict(data)
    result = engine.run()
    assert result["status"] == "success"
    assert result["total_tasks"] == 4

def test_engine_aborts_on_cycle():
    data = {
        "tasks": [
            {"id": "A", "priority": 1, "dependencies": ["C"]},
            {"id": "B", "priority": 1, "dependencies": ["A"]},
            {"id": "C", "priority": 1, "dependencies": ["B"]},
        ]
    }
    engine = WorkflowEngine()
    engine.load_from_dict(data)
    try:
        engine.run()
        assert False, "Deveria ter abortado"
    except RuntimeError as e:
        assert "DEADLOCK" in str(e)

def test_cycle_path_is_complete():
    """Caminho do ciclo deve ser completo: A→B→C→A, não apenas A→C."""
    from src.algorithms import CycleDetector
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")
    det = CycleDetector(g)
    assert det.has_cycle()
    path = det.cycle_path
    assert len(path) == 4, f"Esperado 4 nós no caminho, got {len(path)}: {path}"
    assert path[0] == path[-1], "Caminho deve fechar o loop"

def test_engine_isolated_nodes():
    """Nós isolados (sem deps e sem dependentes) devem executar normalmente."""
    data = {
        "tasks": [
            {"id": "ISO1", "priority": 50, "dependencies": []},
            {"id": "ISO2", "priority": 30, "dependencies": []},
            {"id": "T1",   "priority": 10, "dependencies": []},
        ]
    }
    engine = WorkflowEngine()
    engine.load_from_dict(data)
    result = engine.run()
    assert result["status"] == "success"
    assert result["total_tasks"] == 3
    # ISO1 tem maior prioridade, deve sair primeiro
    assert result["execution_order"][0]["task_id"] == "ISO1"

def test_engine_diamond_pattern():
    """Padrão fork-join: A→B, A→C, B→D, C→D. D deve ser o último."""
    data = {
        "tasks": [
            {"id": "A", "priority": 10, "dependencies": []},
            {"id": "B", "priority": 10, "dependencies": ["A"]},
            {"id": "C", "priority": 10, "dependencies": ["A"]},
            {"id": "D", "priority": 10, "dependencies": ["B", "C"]},
        ]
    }
    engine = WorkflowEngine()
    engine.load_from_dict(data)
    result = engine.run()
    assert result["status"] == "success"
    order_ids = [e["task_id"] for e in result["execution_order"]]
    assert order_ids.index("A") < order_ids.index("D")
    assert order_ids.index("B") < order_ids.index("D")
    assert order_ids.index("C") < order_ids.index("D")

def test_deep_cycle_detection():
    """Ciclo profundo enterrado no meio do grafo deve ser detectado."""
    data = {
        "tasks": [
            {"id": "S",       "priority": 1, "dependencies": []},
            {"id": "CYCLE-0", "priority": 1, "dependencies": ["CYCLE-4"]},
            {"id": "CYCLE-1", "priority": 1, "dependencies": ["CYCLE-0"]},
            {"id": "CYCLE-2", "priority": 1, "dependencies": ["CYCLE-1"]},
            {"id": "CYCLE-3", "priority": 1, "dependencies": ["CYCLE-2"]},
            {"id": "CYCLE-4", "priority": 1, "dependencies": ["CYCLE-3"]},
            {"id": "E",       "priority": 1, "dependencies": []},
        ]
    }
    engine = WorkflowEngine()
    engine.load_from_dict(data)
    try:
        engine.run()
        assert False, "Deveria detectar ciclo profundo"
    except RuntimeError as e:
        assert "DEADLOCK" in str(e)

def test_engine_outputs_json():
    """main.py deve gravar output.json com estrutura correta."""
    import json, subprocess, tempfile, os
    root = Path(__file__).parent.parent
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file  = Path(tmpdir) / "test_input.json"
        output_file = Path(tmpdir) / "test_output.json"
        data = {"tasks": [
            {"id": "X", "priority": 5, "dependencies": []},
            {"id": "Y", "priority": 3, "dependencies": ["X"]},
        ]}
        input_file.write_text(json.dumps(data))
        subprocess.run(
            [sys.executable, str(root / "main.py"),
             str(input_file), str(output_file)],
            check=True, capture_output=True
        )
        assert output_file.exists(), "output.json não foi gerado"
        with open(output_file) as f:
            out = json.load(f)
        assert out["status"] == "success"
        assert out["total_tasks"] == 2
        assert "execution_order" in out


# ══════════════════════════════════════════════════════════════════════ #
#  Runner manual (sem pytest)
# ══════════════════════════════════════════════════════════════════════ #

def _run_all():
    tests = [
        test_graph_add_node, test_graph_add_edge, test_graph_multiple_neighbors,
        test_no_cycle, test_simple_cycle, test_self_loop, test_diamond_no_cycle,
        test_topo_linear_chain, test_topo_raises_on_cycle, test_topo_diamond,
        test_heap_max_order, test_heap_peek_no_remove, test_heap_empty_raises,
        test_heap_build_from,
        test_engine_full_run, test_engine_aborts_on_cycle,
        test_cycle_path_is_complete,
        test_engine_isolated_nodes, test_engine_diamond_pattern,
        test_deep_cycle_detection, test_engine_outputs_json,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  [✓] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [✗] {t.__name__}  →  {e}")
            failed += 1
    print(f"\n  {passed} aprovados, {failed} reprovados.")
    return failed

if __name__ == "__main__":
    print("\n=== Testes Unitários — Workflow Engine ===\n")
    failures = _run_all()
    sys.exit(failures)
