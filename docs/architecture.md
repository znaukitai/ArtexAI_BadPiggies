# Архитектура Artex AI

## Схема работы

```mermaid
flowchart TD
    S[Студент] --> UI[Streamlit frontend/app.py]
    UI --> G[Gateway]
    G -->|Gemini API / Vertex AI| A[ArtexAgent]
    G -->|Локальный режим без ключа| M[MCP Orchestrator]
    A --> B[InMemoryMCPBridge]
    M --> B
    B --> T[Инструменты FastMCP]
    T --> SCH[academic_schedule: дедлайны и план недели]
    T --> GH[campus_services: GitHub REST API]
    T --> MAP[campus_services: карта AITU C1.1-C1.3]
    A --> R[AgentResponse]
    M --> R
    R --> UI
```

## Модули

- `frontend/app.py` — чат-интерфейс, переключение светлой/тёмной темы, быстрые действия и панель дедлайнов.
- `frontend/gateway.py` — шлюз между UI, локальным агентом `ArtexAgent`, оркестратором MCP и облачным Vertex AI.
- `frontend/ui_components.py` — стили тем и карточки задач.
- `agent/` — цикл рассуждений Gemini с вызовом инструментов (`artex_agent.py`), мост инструментов (`mcp_bridge.py`) и модели данных (`models.py`).
- `core/deadline_logic.py` — расчёт срочности, фильтрация задач, парсинг силлабуса и планировщик недели.
- `mcp_servers/` — серверы инструментов `academic_schedule.py` и `campus_services.py`.
- `deployment/deploy.py` — скрипт деплоя в Vertex AI Agent Engine.
