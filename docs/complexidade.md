# Documentação Técnica — Workflow Engine

## 1. Estruturas de Dados Implementadas

### RF01 — Grafo Direcionado com Lista de Adjacência (`src/graph.py`)

Representação interna: `dict[str, list[str]]`

Aresta `A → B` indica *"A deve executar antes de B"*.

| Operação     | Complexidade | Justificativa                          |
|--------------|-------------|----------------------------------------|
| `add_node`   | O(1)        | Inserção em dicionário hash            |
| `add_edge`   | O(1)        | Append em lista                        |
| `neighbors`  | O(1)        | Lookup em dicionário                   |
| Espaço total | O(V + E)    | V entradas + soma dos graus = E        |

**Por que Lista de Adjacência e não Matriz?**

Com 10.000 nós, uma matriz ocuparia 10.000² = 100 milhões de entradas.
Com ~25.000 arestas, apenas 0,025% das células seriam não-nulas.
A lista de adjacência usa O(V + E) = O(35.000), redução de ~2.857×.

---

### RF02 — Ordenação Topológica — Kahn's Algorithm (`src/algorithms.py`)

Algoritmo BFS por in-degree:

```
1. Calcula in_degree[v] para todo v                    → O(V + E)
2. Enfileira nós com in_degree == 0                    → O(V)
3. Processa fila: ao retirar u, decrementa in_degree   → O(E) total
   dos vizinhos; vizinhos que chegam a 0 são enfileirados
4. Se |order| < V → grafo tem ciclo                    → O(1)
```

Complexidade total: **O(V + E)**

Vantagem sobre DFS reversa: produz execução em **camadas** naturais
(tarefas na mesma camada podem ser paralelizadas), e a detecção de
ciclo é subproduto direto sem segunda passagem.

---

### RF03 — Detecção de Ciclos — DFS Tricolor (`src/algorithms.py`)

Coloração de nós em três estados:

| Cor     | Significado                              |
|---------|------------------------------------------|
| `WHITE` | Não visitado                             |
| `GRAY`  | Em processamento — na pilha corrente     |
| `BLACK` | Processamento concluído                  |

Back-edge detectada quando `u → v` e `v` é `GRAY`.

**Implementação iterativa** (pilha explícita em vez de recursão):
evita `RecursionError` do Python (limite padrão: 1.000 frames) para
grafos com dezenas de milhares de nós.

Complexidade: **O(V + E)**

**Reconstrução do caminho do ciclo:**
Percorre o dicionário `parent[]` de `cycle_end` até `cycle_start`,
produzindo o caminho legível `A → B → C → A` para diagnóstico.

---

### RF04 — Fila de Prioridade — Max-Heap Binário (`src/heap.py`)

Array contíguo com indexação base-0:

```
pai(i)       = (i - 1) // 2
filho_esq(i) = 2i + 1
filho_dir(i) = 2i + 2
```

Invariante: `heap[i] ≥ heap[2i+1]` e `heap[i] ≥ heap[2i+2]`

| Operação      | Complexidade | Justificativa                      |
|---------------|-------------|-------------------------------------|
| `insert`      | O(log N)    | sift_up percorre altura = log N     |
| `extract_max` | O(log N)    | sift_down percorre altura = log N   |
| `peek`        | O(1)        | raiz sempre é o máximo              |
| `build_from`  | **O(N)**    | Floyd's heapify — prova abaixo      |

**Prova de O(N) para build_from (Floyd's Heapify):**

Cada nó na altura `h` realiza no máximo `h` swaps no sift_down.
Há no máximo ⌊N/2^(h+1)⌋ nós na altura `h`. Somando:

```
T = Σ(h=0 até ⌊log N⌋)  ⌊N/2^(h+1)⌋ · h
  ≤ N · Σ(h=0 até ∞)  h/2^h
  = N · 2           (série geométrica derivada)
  = O(N)
```

Portanto `build_from` é O(N), mais eficiente que N inserções
sequenciais que custariam O(N log N).

---

## 2. Análise de Complexidade Global

| Fase                    | Algoritmo       | Complexidade |
|-------------------------|-----------------|-------------|
| Carregar JSON           | I/O             | O(N + E)    |
| Construir grafo         | Inserções       | O(N + E)    |
| RF03 — Detectar ciclos  | DFS tricolor    | O(V + E)    |
| RF02 — Ord. topológica  | Kahn's BFS      | O(V + E)    |
| RF04 — Build heap       | Floyd heapify   | O(N)        |
| RF04 — Drain heap       | N × extract_max | O(N log N)  |
| **Total**               |                 | **O(N log N)** |

O gargalo é o drain da heap: N extrações de O(log N) cada.

---

## 3. Edge Cases Cobertos

| Edge Case                         | Onde                  | Como tratado               |
|-----------------------------------|-----------------------|----------------------------|
| Ciclo profundo oculto             | `*_ciclo.json`        | DFS aborta com caminho      |
| Nós completamente isolados        | `input_avancado.json` | In-degree 0, entram na heap |
| Dependências duplicadas           | `input_avancado.json` | Contadas como arestas extra |
| Padrão diamante (fork-join)       | `input_avancado.json` | In-degree correto para Join |
| Grafo vazio                       | `tests/test_engine.py`| Retorna lista vazia         |
| Auto-loop (T → T)                 | `tests/test_engine.py`| Detectado como ciclo        |

---

## 4. Evidências de Performance

Ver seção "Prova de Carga" no `README.md` e executar:

```bash
python scripts/stress_test.py   # métricas reais de tempo e memória
python scripts/benchmark.py     # confirma O(N log N) de 100 a 50.000 nós
```
