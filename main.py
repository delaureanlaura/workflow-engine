
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.engine import WorkflowEngine


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python main.py <input.json> [output.json]")
        print("Exemplo: python main.py data/input_basico.json")
        return 1

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_path}")
        return 1

    # Saída padrão: mesmo diretório, prefixo "output_"
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        stem = input_path.stem.replace("input_", "")
        output_path = input_path.parent / f"output_{stem}.json"

    # ── Execução ──────────────────────────────────────────────────────
    print(f"\n  Workflow Engine")
    print(f"  Entrada : {input_path}")
    print(f"  Saída   : {output_path}")
    print(f"  {'─'*50}")

    engine = WorkflowEngine()

    try:
        t0 = time.perf_counter()
        engine.load_from_file(input_path)
        load_ms = (time.perf_counter() - t0) * 1000

        print(f"  Grafo   : {engine.graph.num_nodes:,} nós, "
              f"{engine.graph.num_edges:,} arestas  ({load_ms:.1f} ms)")

        result = engine.run()

        # ── Grava saída determinística ────────────────────────────────
        output = {
            "status":      result["status"],
            "total_tasks": result["total_tasks"],
            "total_edges": result["total_edges"],
            "elapsed_ms":  result["elapsed_ms"],
            "execution_order": result["execution_order"],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"  Status  : {result['status']}")
        print(f"  Tempo   : {result['elapsed_ms']} ms")
        print(f"  Saída gravada em: {output_path}")

        # Preview no terminal
        print(f"\n  Top 5 tarefas por prioridade:")
        for e in result["execution_order"][:5]:
            print(f"    [{e['step']:>5}] {e['task_id']}  "
                  f"prio={e['priority']:>3}  {e['name']}")
        if result["total_tasks"] > 5:
            print(f"    ... +{result['total_tasks'] - 5:,} tarefas (ver {output_path.name})")

    except RuntimeError as e:
        # Deadlock — ainda grava o output com status de erro
        output = {"status": "aborted", "reason": str(e)}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  [ABORTADO] {e}")
        print(f"  Diagnóstico gravado em: {output_path}")
        return 2

    except Exception as e:
        print(f"\n  [ERRO INESPERADO] {e}")
        raise

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
