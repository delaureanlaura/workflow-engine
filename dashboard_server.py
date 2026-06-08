#!/usr/bin/env python3
"""
Workflow Engine — API HTTP + Dashboard Interativo
Serve o dashboard visual em http://localhost:8000

Uso:
  python dashboard_server.py
  python dashboard_server.py --port 9090
"""

import argparse
import json
import sys
import time
import tracemalloc
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.engine import WorkflowEngine
from src.algorithms import CycleDetector, TopologicalSort
from src.graph import Graph


# ─────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────

def run_scenario(data: dict) -> dict:
    """Executa o pipeline completo e retorna métricas detalhadas."""
    tracemalloc.start()
    t_start = time.perf_counter()

    engine = WorkflowEngine()
    engine.load_from_dict(data)

    num_tasks = engine.graph.num_nodes
    num_edges = engine.graph.num_edges

    # RF03 — DFS
    t0 = time.perf_counter()
    has_cycle = False
    cycle_path = []
    try:
        engine.check_deadlocks()
    except RuntimeError as e:
        has_cycle = True
        cycle_path = str(e)
    dfs_ms = (time.perf_counter() - t0) * 1000

    # RF02 — Topo sort
    t1 = time.perf_counter()
    if not has_cycle:
        order = engine.topological_order()
    else:
        order = []
    topo_ms = (time.perf_counter() - t1) * 1000

    # RF04 — Heap build + drain
    t2 = time.perf_counter()
    if not has_cycle:
        engine.build_ready_queue(order)
    heap_build_ms = (time.perf_counter() - t2) * 1000

    t3 = time.perf_counter()
    execution_log = []
    step = 1
    if not has_cycle:
        while engine.heap:
            task = engine.heap.extract_max()
            execution_log.append({
                "step": step,
                "task_id": task.task_id,
                "name": task.metadata.get("name", task.task_id),
                "priority": task.priority,
            })
            step += 1
    heap_drain_ms = (time.perf_counter() - t3) * 1000

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total_ms = (time.perf_counter() - t_start) * 1000

    # Priority distribution (buckets 0-9, 10-19, ... 90-100)
    all_priorities = [t.get("priority", 1) for t in data["tasks"]]
    buckets = [0] * 10
    for p in all_priorities:
        buckets[min(int(p) // 10, 9)] += 1

    # Degree distribution (in-degree of each node)
    from collections import Counter
    in_degree_counter: dict[str, int] = {t["id"]: 0 for t in data["tasks"]}
    for task in data["tasks"]:
        for dep in task.get("dependencies", []):
            if dep in in_degree_counter:
                in_degree_counter[dep] += 1
    deg_dist = Counter(in_degree_counter.values())
    deg_labels = sorted(deg_dist.keys())[:12]

    # First 20 execution steps for the order preview
    preview = execution_log[:20]

    return {
        "status": "cycle_detected" if has_cycle else "success",
        "cycle_path": cycle_path,
        "num_tasks": num_tasks,
        "num_edges": num_edges,
        "timings": {
            "dfs_ms":        round(dfs_ms, 2),
            "topo_ms":       round(topo_ms, 2),
            "heap_build_ms": round(heap_build_ms, 2),
            "heap_drain_ms": round(heap_drain_ms, 2),
            "total_ms":      round(total_ms, 2),
        },
        "memory_mb":  round(peak / (1024 * 1024), 3),
        "throughput": round(num_tasks / (total_ms / 1000)) if total_ms > 0 else 0,
        "priority_buckets": buckets,
        "degree_dist": {str(k): deg_dist[k] for k in deg_labels},
        "execution_preview": preview,
    }


# ─────────────────────────────────────────────────────────────────────
#  HTTP Handler
# ─────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # Silencia logs do servidor

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/dashboard":
            self.send_html(DASHBOARD_HTML)

        elif path == "/api/scenarios":
            data_dir = ROOT / "data"
            scenarios = []
            for f in sorted(data_dir.glob("*.json")):
                if "_ciclo" not in f.name:
                    scenarios.append({"id": f.stem, "label": f.stem.capitalize(), "path": str(f)})
                else:
                    scenarios.append({"id": f.stem, "label": f.stem + " (deadlock)", "path": str(f)})
            self.send_json({"scenarios": scenarios})

        elif path == "/api/run":
            scenario = params.get("scenario", ["basico"])[0]
            json_path = ROOT / "data" / f"{scenario}.json"
            if not json_path.exists():
                self.send_json({"error": f"Cenário '{scenario}' não encontrado."}, 404)
                return
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            result = run_scenario(data)
            self.send_json(result)

        elif path == "/api/run_custom":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                result = run_scenario(data)
                self.send_json(result)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ─────────────────────────────────────────────────────────────────────
#  Dashboard HTML (injetado inline)
# ─────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Workflow Engine — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1117; --bg2: #171b26; --bg3: #1e2332;
    --border: rgba(255,255,255,0.08); --border2: rgba(255,255,255,0.14);
    --text: #e8eaf0; --muted: #7a82a0; --accent: #6c8eef;
    --green: #4ade80; --amber: #fbbf24; --red: #f87171; --teal: #2dd4bf;
    --radius: 10px; --font: 'Inter', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 14px; line-height: 1.6; min-height: 100vh; }
  a { color: var(--accent); }

  /* Layout */
  .app { display: grid; grid-template-rows: 56px 1fr; min-height: 100vh; }
  header { background: var(--bg2); border-bottom: 1px solid var(--border); display: flex; align-items: center; padding: 0 24px; gap: 16px; }
  header h1 { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
  header .badge { font-size: 11px; background: rgba(108,142,239,0.15); color: var(--accent); border: 1px solid rgba(108,142,239,0.25); border-radius: 20px; padding: 2px 10px; }
  main { padding: 24px; display: flex; flex-direction: column; gap: 20px; max-width: 1400px; margin: 0 auto; width: 100%; }

  /* Controls */
  .controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  select, button { background: var(--bg2); border: 1px solid var(--border2); color: var(--text); border-radius: 8px; padding: 8px 14px; font-size: 13px; font-family: inherit; cursor: pointer; transition: background .15s, border-color .15s; outline: none; }
  select:focus, button:focus { border-color: var(--accent); }
  button.primary { background: var(--accent); color: #fff; border-color: transparent; font-weight: 600; }
  button.primary:hover { background: #5a7de0; }
  button.primary:disabled { opacity: .4; cursor: not-allowed; }
  .status-pill { font-size: 12px; border-radius: 20px; padding: 3px 12px; font-weight: 500; }
  .status-pill.ok  { background: rgba(74,222,128,0.12); color: var(--green); border: 1px solid rgba(74,222,128,0.25); }
  .status-pill.err { background: rgba(248,113,113,0.12); color: var(--red);   border: 1px solid rgba(248,113,113,0.25); }
  .status-pill.idle { background: rgba(122,130,160,0.1); color: var(--muted); border: 1px solid var(--border); }

  /* Metric cards */
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
  .card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 18px; }
  .card .label { font-size: 11px; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
  .card .value { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; color: var(--text); line-height: 1; }
  .card .sub   { font-size: 11px; color: var(--muted); margin-top: 4px; }
  .card.accent { border-color: rgba(108,142,239,0.3); }
  .card.accent .value { color: var(--accent); }
  .card.green  { border-color: rgba(74,222,128,0.25); }
  .card.green  .value { color: var(--green); }
  .card.amber  { border-color: rgba(251,191,36,0.25); }
  .card.amber  .value { color: var(--amber); }

  /* Timing breakdown */
  .pipeline { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
  .pipeline h2 { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 16px; }
  .pipe-steps { display: flex; flex-direction: column; gap: 10px; }
  .pipe-row { display: grid; grid-template-columns: 160px 1fr 64px; align-items: center; gap: 12px; }
  .pipe-row .name { font-size: 13px; color: var(--muted); }
  .pipe-row .bar-track { background: var(--bg3); border-radius: 4px; height: 8px; overflow: hidden; }
  .pipe-row .bar-fill  { height: 100%; border-radius: 4px; transition: width .5s cubic-bezier(.4,0,.2,1); }
  .pipe-row .ms { font-size: 12px; color: var(--text); text-align: right; font-variant-numeric: tabular-nums; }

  /* Charts grid */
  .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 860px) { .charts { grid-template-columns: 1fr; } }
  .chart-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
  .chart-card h2 { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 14px; }

  /* Execution log */
  .log-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
  .log-card h2 { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 14px; }
  .log-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .log-table th { color: var(--muted); text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--border); font-weight: 500; }
  .log-table td { padding: 7px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); }
  .log-table tr:last-child td { border-bottom: none; }
  .prio-badge { display: inline-block; width: 32px; text-align: center; border-radius: 4px; padding: 2px 0; font-weight: 600; font-size: 11px; }

  /* Pipeline animation */
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  .running .primary { animation: pulse .8s ease-in-out infinite; }

  /* Complexity section */
  .complexity { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 700px) { .complexity { grid-template-columns: 1fr; } }
  .complexity h2 { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 14px; grid-column: 1/-1; }
  .algo { display: flex; flex-direction: column; gap: 8px; }
  .algo-row { display: flex; align-items: flex-start; gap: 12px; padding: 10px 12px; background: var(--bg3); border-radius: 8px; border: 1px solid var(--border); }
  .algo-row .rf  { font-size: 11px; font-weight: 700; color: var(--accent); min-width: 36px; }
  .algo-row .name { font-size: 13px; font-weight: 600; color: var(--text); }
  .algo-row .big-o { font-size: 12px; font-family: 'JetBrains Mono', 'Fira Code', monospace; background: rgba(108,142,239,0.1); color: var(--accent); border-radius: 4px; padding: 2px 7px; }
  .algo-row p { font-size: 12px; color: var(--muted); margin-top: 3px; }

  /* Deadlock warning */
  .deadlock-banner { background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.25); border-radius: 8px; padding: 14px 18px; display: none; }
  .deadlock-banner.show { display: block; }
  .deadlock-banner strong { color: var(--red); display: block; margin-bottom: 4px; }
  .deadlock-banner code { font-family: monospace; font-size: 12px; color: var(--muted); }
</style>
</head>
<body>
<div class="app">
  <header>
    <div style="width:28px;height:28px;background:var(--accent);border-radius:7px;display:flex;align-items:center;justify-content:center;">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="3" r="2" fill="white" opacity=".7"/><circle cx="13" cy="3" r="2" fill="white"/><circle cx="8" cy="13" r="2" fill="white" opacity=".7"/><line x1="5" y1="3" x2="11" y2="3" stroke="white" stroke-width="1.2"/><line x1="3" y1="5" x2="7.2" y2="11.2" stroke="white" stroke-width="1.2"/><line x1="13" y1="5" x2="8.8" y2="11.2" stroke="white" stroke-width="1.2"/></svg>
    </div>
    <h1>Workflow Engine</h1>
    <span class="badge">Orquestrador de Agentes Autônomos</span>
    <div style="flex:1"></div>
    <span id="status-pill" class="status-pill idle">Aguardando</span>
  </header>

  <main>
    <!-- Controls -->
    <div class="controls">
      <select id="scenario-select">
        <option value="">Carregando cenários...</option>
      </select>
      <button class="primary" id="run-btn" onclick="runScenario()">▶ Executar Pipeline</button>
    </div>

    <!-- Deadlock banner -->
    <div id="deadlock-banner" class="deadlock-banner">
      <strong>🔴 DEADLOCK DETECTADO — Execução Abortada</strong>
      <code id="deadlock-path"></code>
    </div>

    <!-- Metric cards -->
    <div class="metrics">
      <div class="card accent"><div class="label">Tarefas</div><div class="value" id="m-tasks">—</div><div class="sub">no workflow</div></div>
      <div class="card accent"><div class="label">Arestas</div><div class="value" id="m-edges">—</div><div class="sub">dependências</div></div>
      <div class="card green"><div class="label">Tempo Total</div><div class="value" id="m-time">—</div><div class="sub">milissegundos</div></div>
      <div class="card green"><div class="label">Throughput</div><div class="value" id="m-thru">—</div><div class="sub">tarefas / segundo</div></div>
      <div class="card amber"><div class="label">Memória Pico</div><div class="value" id="m-mem">—</div><div class="sub">megabytes</div></div>
      <div class="card"><div class="label">Densidade</div><div class="value" id="m-dens">—</div><div class="sub">arestas / nó</div></div>
    </div>

    <!-- Pipeline timing -->
    <div class="pipeline">
      <h2>Pipeline de Execução — Tempo por Fase</h2>
      <div class="pipe-steps" id="pipe-steps">
        <div class="pipe-row"><div class="name">RF03 · DFS Ciclos</div><div class="bar-track"><div class="bar-fill" id="bar-dfs" style="width:0%;background:#6c8eef;"></div></div><div class="ms" id="t-dfs">—</div></div>
        <div class="pipe-row"><div class="name">RF02 · Ord. Topológica</div><div class="bar-track"><div class="bar-fill" id="bar-topo" style="width:0%;background:#4ade80;"></div></div><div class="ms" id="t-topo">—</div></div>
        <div class="pipe-row"><div class="name">RF04 · Build Heap</div><div class="bar-track"><div class="bar-fill" id="bar-heap" style="width:0%;background:#fbbf24;"></div></div><div class="ms" id="t-heap">—</div></div>
        <div class="pipe-row"><div class="name">RF04 · Drain Heap</div><div class="bar-track"><div class="bar-fill" id="bar-drain" style="width:0%;background:#2dd4bf;"></div></div><div class="ms" id="t-drain">—</div></div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts">
      <div class="chart-card">
        <h2>Distribuição de Prioridade</h2>
        <div style="position:relative;height:220px;"><canvas id="chart-prio" role="img" aria-label="Histograma de prioridade das tarefas"></canvas></div>
      </div>
      <div class="chart-card">
        <h2>Distribuição de In-Degree</h2>
        <div style="position:relative;height:220px;"><canvas id="chart-deg" role="img" aria-label="Distribuição de in-degree dos nós"></canvas></div>
      </div>
    </div>

    <!-- Complexity reference -->
    <div class="complexity">
      <h2>Análise de Complexidade — Estruturas Implementadas</h2>
      <div class="algo">
        <div class="algo-row"><div class="rf">RF01</div><div><div class="name" style="display:flex;align-items:center;gap:8px;">Grafo — Lista de Adjacência <span class="big-o">O(V+E)</span></div><p>dict[str, list[str]]. Esparso: usa N× menos memória que matriz. add_edge e neighbors em O(1).</p></div></div>
        <div class="algo-row"><div class="rf">RF03</div><div><div class="name" style="display:flex;align-items:center;gap:8px;">DFS Tricolor <span class="big-o">O(V+E)</span></div><p>WHITE / GRAY / BLACK. Back-edge em nó GRAY = ciclo. Iterativo para evitar RecursionError em 10 000+ nós.</p></div></div>
      </div>
      <div class="algo">
        <div class="algo-row"><div class="rf">RF02</div><div><div class="name" style="display:flex;align-items:center;gap:8px;">Kahn's Algorithm <span class="big-o">O(V+E)</span></div><p>BFS por in-degree. Garante ordem por camadas, detecta ciclo residual se |order| &lt; V.</p></div></div>
        <div class="algo-row"><div class="rf">RF04</div><div><div class="name" style="display:flex;align-items:center;gap:8px;">Max-Heap Binário <span class="big-o">O(N log N)</span></div><p>Build de Floyd O(N). insert/extract em O(log N). Pai(i)=(i-1)//2, filhos 2i+1 e 2i+2.</p></div></div>
      </div>
    </div>

    <!-- Execution log -->
    <div class="log-card">
      <h2>Ordem de Execução — Top 20 por Prioridade</h2>
      <table class="log-table">
        <thead><tr><th>#</th><th>ID</th><th>Nome</th><th>Prioridade</th></tr></thead>
        <tbody id="log-body"><tr><td colspan="4" style="color:var(--muted);text-align:center;padding:24px;">Execute um cenário para ver a ordem de execução.</td></tr></tbody>
      </table>
    </div>
  </main>
</div>

<script>
// ── Charts ──────────────────────────────────────────────────────────
const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#7a82a0', font: { size: 11 } } },
    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#7a82a0', font: { size: 11 } } }
  }
};
let chartPrio = new Chart(document.getElementById('chart-prio'), {
  type: 'bar',
  data: { labels: ['0-9','10-19','20-29','30-39','40-49','50-59','60-69','70-79','80-89','90+'], datasets: [{
    data: new Array(10).fill(0),
    backgroundColor: 'rgba(108,142,239,0.55)',
    borderColor: '#6c8eef', borderWidth: 1,
  }]},
  options: { ...CHART_OPTS, plugins: { ...CHART_OPTS.plugins } }
});
let chartDeg = new Chart(document.getElementById('chart-deg'), {
  type: 'bar',
  data: { labels: [], datasets: [{
    data: [],
    backgroundColor: 'rgba(45,212,191,0.55)',
    borderColor: '#2dd4bf', borderWidth: 1,
  }]},
  options: { ...CHART_OPTS }
});

// ── Load scenarios ────────────────────────────────────────────────
async function loadScenarios() {
  const res  = await fetch('/api/scenarios');
  const json = await res.json();
  const sel  = document.getElementById('scenario-select');
  sel.innerHTML = json.scenarios.map(s =>
    `<option value="${s.id}">${s.label}</option>`
  ).join('');
}

// ── Run ──────────────────────────────────────────────────────────
async function runScenario() {
  const btn  = document.getElementById('run-btn');
  const pill = document.getElementById('status-pill');
  const sc   = document.getElementById('scenario-select').value;
  if (!sc) return;

  btn.disabled = true;
  document.body.classList.add('running');
  pill.className = 'status-pill idle';
  pill.textContent = 'Executando...';

  document.getElementById('deadlock-banner').classList.remove('show');

  try {
    const res  = await fetch(`/api/run?scenario=${encodeURIComponent(sc)}`);
    const data = await res.json();
    render(data);
    pill.className = data.status === 'success' ? 'status-pill ok' : 'status-pill err';
    pill.textContent = data.status === 'success' ? '✓ Concluído' : '✗ Deadlock';
  } catch(e) {
    pill.className = 'status-pill err';
    pill.textContent = 'Erro de rede';
  } finally {
    btn.disabled = false;
    document.body.classList.remove('running');
  }
}

function render(data) {
  // Metrics
  document.getElementById('m-tasks').textContent = data.num_tasks.toLocaleString('pt-BR');
  document.getElementById('m-edges').textContent = data.num_edges.toLocaleString('pt-BR');
  document.getElementById('m-time').textContent  = data.timings.total_ms.toFixed(1);
  document.getElementById('m-thru').textContent  = data.throughput.toLocaleString('pt-BR');
  document.getElementById('m-mem').textContent   = data.memory_mb.toFixed(2);
  document.getElementById('m-dens').textContent  = (data.num_edges / data.num_tasks).toFixed(1);

  // Deadlock
  if (data.status !== 'success') {
    document.getElementById('deadlock-banner').classList.add('show');
    document.getElementById('deadlock-path').textContent = data.cycle_path;
  }

  // Pipeline bars
  const t  = data.timings;
  const max = Math.max(t.dfs_ms, t.topo_ms, t.heap_build_ms, t.heap_drain_ms, 0.1);
  const pct = v => Math.max(2, (v / max * 100)).toFixed(1) + '%';
  document.getElementById('bar-dfs').style.width   = pct(t.dfs_ms);
  document.getElementById('bar-topo').style.width  = pct(t.topo_ms);
  document.getElementById('bar-heap').style.width  = pct(t.heap_build_ms);
  document.getElementById('bar-drain').style.width = pct(t.heap_drain_ms);
  document.getElementById('t-dfs').textContent   = t.dfs_ms.toFixed(2) + ' ms';
  document.getElementById('t-topo').textContent  = t.topo_ms.toFixed(2) + ' ms';
  document.getElementById('t-heap').textContent  = t.heap_build_ms.toFixed(2) + ' ms';
  document.getElementById('t-drain').textContent = t.heap_drain_ms.toFixed(2) + ' ms';

  // Charts
  chartPrio.data.datasets[0].data = data.priority_buckets;
  chartPrio.update();
  const degLabels = Object.keys(data.degree_dist);
  const degValues = Object.values(data.degree_dist);
  chartDeg.data.labels = degLabels.map(k => 'grau ' + k);
  chartDeg.data.datasets[0].data = degValues;
  chartDeg.update();

  // Log
  const tbody = document.getElementById('log-body');
  if (!data.execution_preview || data.execution_preview.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:16px;">Pipeline abortado por deadlock.</td></tr>`;
    return;
  }
  tbody.innerHTML = data.execution_preview.map(r => {
    const pct = r.priority;
    const hue = Math.floor(pct * 1.2);
    const bg  = `hsl(${hue},60%,25%)`;
    const fg  = `hsl(${hue},80%,70%)`;
    return `<tr>
      <td style="color:var(--muted)">${r.step}</td>
      <td style="font-family:monospace;font-size:11px;color:var(--accent)">${r.task_id}</td>
      <td>${r.name}</td>
      <td><span class="prio-badge" style="background:${bg};color:${fg}">${r.priority}</span></td>
    </tr>`;
  }).join('');
}

// ── Boot ──────────────────────────────────────────────────────────
loadScenarios().then(() => {
  // Auto-run o cenário básico ao abrir
  setTimeout(() => runScenario(), 200);
});
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = HTTPServer(("", args.port), Handler)
    print(f"\n  Workflow Engine Dashboard")
    print(f"  ─────────────────────────")
    print(f"  http://localhost:{args.port}")
    print(f"\n  Ctrl+C para encerrar\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor encerrado.")


if __name__ == "__main__":
    main()
