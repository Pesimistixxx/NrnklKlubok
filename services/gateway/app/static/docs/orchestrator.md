# Оркестратор L1–L6

Режим **Оркестратор** (`orchestrator_mode`) — LangGraph-граф с **гибким циклом** межслойных агентов,
**JSON-шиной** (`agent_bus`) и финальным синтезом.

> Спецификации layer agents — в разделе **Межслойные агенты (L1–L6)**. Здесь — узлы оркестратора и маршрутизация.

UI cache: `?v=78` (при странном поведении — **Ctrl+F5**).

## Поток LangGraph

```mermaid
flowchart TB
  INIT[orchestrator_init] --> PLAN[orchestrator_plan]
  PLAN --> LOOP[agent_loop_start]
  LOOP --> ROUTER[orchestrator_router]

  subgraph FLEX ["Гибкий цикл"]
    ROUTER --> Lx[l*_agent]
    Lx --> ROUTER
  end

  ROUTER --> DISC[discover_new_connections]
  DISC --> GAP[connection_gap_analyzer]
  GAP -->|gap в шину| ROUTER
  GAP --> SYN[orchestrator_synthesize]
  SYN --> END([ответ])
```

Код: `services/agents/app/orchestrator_graph.py` · шина: `agent_bus.py` · агенты: `layer_nodes.py`.

## Узлы оркестратора

| Узел | Назначение |
|------|------------|
| `orchestrator_init` | Документы, пустой граф, инициализация `agent_bus` |
| `orchestrator_plan` | LLM: `planned_layers`, `priority_layers` |
| `agent_loop_start` | `round=0`, `max_rounds=AGENT_LOOP_MAX_ROUNDS` |
| `orchestrator_router` | Выбор следующего `l*_agent` или `discover` |
| `discover_new_connections` | Cross-layer пути Neo4j |
| `connection_gap_analyzer` | Пробелы → `gap_found` в шину или synthesize |
| `orchestrator_synthesize` | Финальный ответ |

## Конфигурация

```env
AGENT_LOOP_MAX_ROUNDS=4
```

## API

```http
POST /api/v1/agents-service/run
{
  "query": "…",
  "mode": "orchestrator_mode"
}
```

Trace: `orchestrator_router` с `next_agent`, `bus_preview`; шаги агентов с `round`, `bus_messages`.

## Связанные разделы

- **Межслойные агенты (L1–L6)** — схема шины, алгоритм цикла
- **Чат, роли и AI-агенты** — UI trace, fallback
