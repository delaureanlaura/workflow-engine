# Workflow Engine — Orquestrador de Agentes Autônomos

Motor de execução que resolve a ordem exata de milhares de tarefas dependentes. Todas as estruturas de dados são implementadas manualmente — nenhuma biblioteca externa de grafos, heap ou algoritmos.

---

## Sumário

1. [Como Executar](#como-executar)
2. [Estrutura do Projeto](#estrutura-do-projeto)
3. [Requisitos Funcionais](#requisitos-funcionais)
4. [Justificativa Teórica](#justificativa-teórica)
5. [Engenharia de Dados](#engenharia-de-dados)
6. [Prova de Carga](#prova-de-carga)
7. [Benchmark de Complexidade](#benchmark-de-complexidade)
8. [Análise de Paralelismo](#análise-de-paralelismo)
9. [Dashboard Interativo](#dashboard-interativo)
10. [Formato JSON](#formato-json)

---

## Como Executar

**Pré-requisito:** Python 3.10+, nenhuma dependência externa.

```bash
# 1. Gerar os dados de teste (3 cenários + versões com deadlock)
python scripts/generate_data.py

# 2. Rodar o motor em um workflow
python main.py data/basico.json
python main.py data/estresse.json

# 3. Testar detecção de deadlock
python main.py data/basico_ciclo.json

# 4. Testes unitários (16 casos)
python tests/test_engine.py

# 5. Prova de carga completa com métricas
python scripts/stress_test.py

# 6. Benchmark de complexidade (100 a 50.000 nós)
python scripts/benchmark.py

# 7. Dashboard visual interativo
python dashboard_server.py
# → Abrir http://localhost:8000
```

---

## Estrutura do Projeto

```
workflow-engine/
├── src/
│   ├── graph.py          # RF01 — Grafo Direcionado (Lista de Adjacência)
│   ├── algorithms.py     # RF02 — Kahn | RF03 — DFS tricolor
│   ├── heap.py           # RF04 — Max-Heap binário (Floyd build)
│   ├── engine.py         # Orquestrador: integra todos os RFs
│   └── analysis.py       # LayerAnalyzer + GraphMetrics (extras)
├── scripts/
│   ├── generate_data.py  # Gera automaticamente basico/avancado/estresse.json
│   ├── stress_test.py    # Prova de carga com métricas de tempo e memória
│   └── benchmark.py      # Confirma complexidade O(N log N) empiricamente
├── tests/
│   └── test_engine.py    # 16 testes unitários (sem pytest)
├── data/                 # JSONs gerados (não versionados)
├── dashboard_server.py   # API HTTP + dashboard interativo
└── main.py               # CLI de execução
```

---

## Requisitos Funcionais

### RF01 — Grafo Direcionado com Lista de Adjacência

`src/graph.py` — representação via `dict[str, list[str]]`.

Aresta `A → B` significa *"A deve executar antes de B"*. Escolha justificada pela esparsidade dos workflows reais: com 10.000 nós e ~25.000 arestas, uma matriz custaria 10.000² = 100 M entradas; a lista de adjacência usa apenas 35.000.

```
Espaço: O(V + E)   add_node/add_edge: O(1)   neighbors(u): O(1)
```

### RF02 — Ordenação Topológica (Kahn's Algorithm)

`src/algorithms.py` → `TopologicalSort`

Algoritmo de Kahn em BFS:
1. Calcula `in-degree` de cada nó.
2. Enfileira nós com `in-degree == 0`.
3. Ao processar `u`, reduz in-degree dos vizinhos; vizinhos que chegam a 0 entram na fila.
4. Se `|order| < V` ao final, o grafo tem ciclo.

Produz a execução por **camadas** (tarefas sem dependência entre si ficam juntas), o que expõe o paralelismo máximo do workflow.

```
Tempo: O(V + E)   Espaço: O(V)
```

### RF03 — Detecção de Ciclos via DFS (coloração tricolor)

`src/algorithms.py` → `CycleDetector`

Três estados por nó:

| Cor     | Estado                      |
|---------|-----------------------------|
| `WHITE` | Não visitado                |
| `GRAY`  | Na pilha de execução atual  |
| `BLACK` | Processamento completo      |

Uma aresta `u → v` onde `v` é `GRAY` é uma **back-edge** — prova de ciclo. A execução é abortada com o caminho do deadlock reconstruído.

Implementação **iterativa** (pilha explícita) para evitar `RecursionError` em grafos com 50.000+ nós.

```
Tempo: O(V + E)   Espaço: O(V)
```

### RF04 — Fila de Prioridade (Max-Heap Binário)

`src/heap.py` → `MaxHeap`

Heap binário sobre `list` com indexação base-0:

```
pai(i)       = (i - 1) // 2
filho_esq(i) = 2i + 1
filho_dir(i) = 2i + 2
```

Invariante: `heap[i] ≥ heap[2i+1]` e `heap[i] ≥ heap[2i+2]`

`build_from(L)` usa **Floyd's heapify** — percorre os nós internos de trás para frente aplicando `sift_down`. Complexidade O(N), em vez de O(N log N) de N inserções sequenciais:

$$\sum_{h=0}^{\lfloor \log N \rfloor} \left\lfloor \frac{N}{2^{h+1}} \right\rfloor \cdot h = O(N)$$

| Operação      | Complexidade |
|---------------|-------------|
| `insert`      | O(log N)    |
| `extract_max` | O(log N)    |
| `peek`        | O(1)        |
| `build_from`  | **O(N)**    |

---

## Justificativa Teórica

### Por que Lista de Adjacência?

Grafos de workflow são **esparsos** — cada tarefa tem poucas dependências (tipicamente 1–5). A matriz de adjacência custaria O(V²) de memória, inviável para escala. A lista de adjacência mantém O(V + E), onde E << V².

### Por que Kahn e não DFS topológico?

O algoritmo de Kahn é preferível ao DFS reverso por dois motivos:
1. Detecta naturalmente **camadas** de execução paralela.
2. A detecção de ciclo é um subproduto direto (`|order| < V`), sem precisar de uma segunda passagem.

### Por que Max-Heap e não ordenação a cada inserção?

Com tarefas chegando dinamicamente (à medida que predecessores completam), manter a lista ordenada custaria O(N) por inserção. O heap garante O(log N) para insert e extract_max, independente do tamanho da fila.

---

## Engenharia de Dados

`scripts/generate_data.py` — geração automática, sem hardcode.

O DAG é gerado garantidamente acíclico: a tarefa `T[i]` só pode depender de tarefas `T[j]` com `j < i`. Isso cria uma ordem topológica natural por construção.

| Arquivo           | Tarefas |  Arestas | Tamanho |
|-------------------|--------:|---------:|--------:|
| `basico.json`     |      50 |     ~100 |   ~9 KB |
| `avancado.json`   |     500 |   ~1.150 |  ~91 KB |
| `estresse.json`   |  10.000 |  ~25.000 | ~1.2 MB |
| `*_ciclo.json`    |    idem |     idem |    idem |

Os arquivos `*_ciclo.json` injetam um back-edge deliberado nos últimos 3 nós para validar o RF03.

---

## Prova de Carga

```
══════════════════════════════════════════════════════════
  CENÁRIO: Básico  (50 tarefas, 103 arestas)
──────────────────────────────────────────────────────────
  RF03 DFS (ciclos)        :     0.40 ms  → SEM CICLO ✓
  RF02 Ordenação Topológica:     0.26 ms
  RF04 Build Max-Heap      :     0.63 ms
  RF04 Drain Heap (50)     :     0.17 ms
  TOTAL                    :     1.46 ms  |  0.03 MB
  Throughput               :   34.289 tarefas/s

══════════════════════════════════════════════════════════
  CENÁRIO: Avançado  (500 tarefas, 1.156 arestas)
──────────────────────────────────────────────────────────
  RF03 DFS (ciclos)        :     1.60 ms  → SEM CICLO ✓
  RF02 Ordenação Topológica:     1.99 ms
  RF04 Build Max-Heap      :     2.17 ms
  RF04 Drain Heap (500)    :     3.97 ms
  TOTAL                    :     9.74 ms  |  0.27 MB
  Throughput               :   51.324 tarefas/s

══════════════════════════════════════════════════════════
  CENÁRIO: Estresse  (10.000 tarefas, 24.968 arestas)
──────────────────────────────────────────────────────────
  RF03 DFS (ciclos)        :    35.91 ms  → SEM CICLO ✓
  RF02 Ordenação Topológica:    45.13 ms
  RF04 Build Max-Heap      :    53.93 ms
  RF04 Drain Heap (10.000) :   184.97 ms
  TOTAL                    :   319.94 ms  |  4.68 MB
  Throughput               :   31.256 tarefas/s

══════════════════════════════════════════════════════════
  VALIDAÇÃO RF03 — Deadlocks
──────────────────────────────────────────────────────────
  [✓] basico_ciclo.json    → detectado em  0.04 ms
  [✓] avancado_ciclo.json  → detectado em  0.12 ms
  [✓] estresse_ciclo.json  → detectado em  2.72 ms
══════════════════════════════════════════════════════════
```

**10.000 tarefas processadas em 320 ms com 4.68 MB de memória.**

---

## Benchmark de Complexidade

`scripts/benchmark.py` — confirma empiricamente O(N log N).

```
       N         E    DFS ms   Kahn ms   Heap ms   Total ms  E/(N log N)
────────────────────────────────────────────────────────────────────────
     100       390      0.13      0.13      0.52       0.78        0.587
     500     1,990      0.58      1.52      2.62       4.72        0.444
   1,000     3,990      1.18      1.28      5.76       8.21        0.400
   5,000    19,990      7.20      7.88     35.67      50.75        0.325
  10,000    39,990     15.54     22.29    135.38     173.21        0.301
  50,000   199,990    126.44    159.50    512.29     798.23        0.256
```

A coluna `E/(N log N)` permanece aproximadamente constante conforme N cresce, confirmando que o sistema escala dentro do limite teórico O(N log N).

---

## Análise de Paralelismo

`src/analysis.py` — `LayerAnalyzer` e `GraphMetrics`.

O analisador de camadas divide o workflow em níveis de execução paralela. Cada camada pode ser executada simultaneamente em produção.

```
Cenário básico (50 tarefas):
  Camadas topológicas : 10
  Fator de paralelismo: 5.0 tarefas/camada em média
  Fontes (sem deps)   : 17
  Sumidouros (sem suc): 9
  Densidade do grafo  : 0.042 (esparso)
```

---

## Dashboard Interativo

`dashboard_server.py` — servidor HTTP + UI visual.

```bash
python dashboard_server.py
# → http://localhost:8000
```

Funcionalidades:
- Execução ao vivo de qualquer cenário
- Barras de progresso por fase (DFS / Kahn / Heap)
- Histograma de prioridades
- Distribuição de in-degree
- Top 20 tarefas na ordem de execução com badge de prioridade colorido
- Detecção e banner de deadlock em tempo real
- API REST em `/api/run?scenario=estresse`

---

## Formato JSON

```json
{
  "tasks": [
    {
      "id": "T000001",
      "name": "Agente-1",
      "priority": 87,
      "duration_ms": 1200,
      "dependencies": ["T000000"]
    }
  ]
}
```

| Campo          | Tipo     | Descrição                                       |
|----------------|----------|-------------------------------------------------|
| `id`           | string   | Identificador único                             |
| `name`         | string   | Nome legível                                    |
| `priority`     | integer  | Urgência (1–100). Maior = executado primeiro    |
| `duration_ms`  | integer  | Duração estimada em ms                          |
| `dependencies` | string[] | IDs que devem executar antes desta tarefa       |
