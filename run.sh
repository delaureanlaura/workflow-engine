#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# run.sh — Script padrão de execução do Workflow Engine
# Exigido pelo template obrigatório do repositório.
#
# Uso:
#   ./run.sh                         → roda todos os cenários
#   ./run.sh generate                → apenas gera os dados de teste
#   ./run.sh basico                  → roda o cenário básico
#   ./run.sh avancado                → roda o cenário avançado
#   ./run.sh estresse                → roda o cenário de estresse
#   ./run.sh test                    → executa os testes unitários
#   ./run.sh benchmark               → benchmark de complexidade
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

PYTHON=${PYTHON:-python3}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Verificação de Python ─────────────────────────────────────────
check_python() {
  if ! command -v "$PYTHON" &>/dev/null; then
    echo "[ERRO] Python não encontrado. Instale Python 3.10+."
    exit 1
  fi
  ver=$("$PYTHON" -c "import sys; print(sys.version_info[:2])")
  echo "  Python: $($PYTHON --version)  ($ver)"
}

# ── Geração de dados ──────────────────────────────────────────────
generate() {
  echo ""
  echo "  Gerando dados de teste..."
  "$PYTHON" "$ROOT/scripts/generate_data.py"
}

# ── Execução de cenário ───────────────────────────────────────────
run_scenario() {
  local name="$1"
  local input="$ROOT/data/input_${name}.json"
  local output="$ROOT/data/output_${name}.json"

  if [ ! -f "$input" ]; then
    echo "  [!] Arquivo não encontrado: $input"
    echo "      Execute: ./run.sh generate"
    exit 1
  fi

  echo ""
  "$PYTHON" "$ROOT/main.py" "$input" "$output"
}

# ── Testes unitários ──────────────────────────────────────────────
run_tests() {
  echo ""
  echo "  Executando testes unitários..."
  "$PYTHON" "$ROOT/tests/test_engine.py"
}

# ── Benchmark ─────────────────────────────────────────────────────
run_benchmark() {
  echo ""
  echo "  Executando benchmark de complexidade..."
  "$PYTHON" "$ROOT/scripts/benchmark.py"
}

# ── Prova de carga ────────────────────────────────────────────────
run_stress() {
  echo ""
  echo "  Executando prova de carga completa..."
  "$PYTHON" "$ROOT/scripts/stress_test.py"
}

# ── Main ──────────────────────────────────────────────────────────
cmd="${1:-all}"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Workflow Engine — run.sh           ║"
echo "  ╚══════════════════════════════════════╝"
check_python

case "$cmd" in
  generate)   generate ;;
  basico)     run_scenario "basico" ;;
  avancado)   run_scenario "avancado" ;;
  estresse)   run_scenario "estresse" ;;
  test)       run_tests ;;
  benchmark)  run_benchmark ;;
  stress)     run_stress ;;
  all)
    generate
    run_scenario "basico"
    run_scenario "avancado"
    run_scenario "estresse"
    run_tests
    echo ""
    echo "  ✓ Pipeline completo executado com sucesso."
    ;;
  *)
    echo "  Uso: ./run.sh [generate|basico|avancado|estresse|test|benchmark|stress|all]"
    exit 1
    ;;
esac

echo ""
