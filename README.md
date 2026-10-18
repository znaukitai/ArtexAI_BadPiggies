# CampusPulse

Помощник студента Astana IT University (AITU). В одном окне объединяет контроль дедлайнов, проверку репозиториев GitHub, составление учебного расписания на неделю и поиск кабинетов по карте кампуса.

Репозиторий проекта: [znaukitai/CampusPulseAI_BadPiggies](https://github.com/znaukitai/CampusPulseAI_BadPiggies)

## Возможности

- **Умный агент:** работает через Google Gemini Function Calling и набор MCP-инструментов (`academic_schedule`, `campus_services`). Если ключ Gemini не задан, автоматически работает встроенный оркестратор MCP-инструментов.
- **Контроль дедлайнов:** расчёт оставшихся дней и приоритетов в часовом поясе `Asia/Almaty`, извлечение дат из текста силлабуса с предпросмотром.
- **Проверка GitHub:** живая проверка статуса репозитория, последних коммитов и наличия обязательных файлов лабораторных работ через GitHub REST API.
- **Карта кампуса AITU:** локальный справочник корпусов C1.1–C1.3 (этажи 1–3) и встроенная интерактивная схема.
- **Светлая и тёмная тема:** минималистичный интерфейс в стиле современных чат-приложений с переключением темы оформления.

## Быстрый старт (Windows)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

После запуска откройте `http://localhost:8501`.

## Настройка `.env`

```dotenv
GEMINI_API_KEY=ваш_ключ
GEMINI_MODEL=gemini-2.5-flash
CAMPUSPULSE_LOCAL_MODE=auto
GITHUB_REPOSITORY=znaukitai/CampusPulseAI_BadPiggies
```

Ключ `GEMINI_API_KEY` и репозиторий также можно указать прямо в боковой панели интерфейса («Подключение и GitHub»).

## Инструменты MCP

| Инструмент | Описание |
|---|---|
| `get_today` | Текущая дата и время (`Asia/Almaty`) |
| `list_deadlines` | Список активных дедлайнов с расчётом срочности |
| `add_deadline` | Добавление новой задачи в расписание |
| `plan_week` | Распределение учебной нагрузки на 7 дней |
| `parse_syllabus_text` | Извлечение дедлайнов из текста силлабуса |
| `github_repo_status` | Метаданные и последние коммиты GitHub-репозитория |
| `github_assignment_check` | Проверка наличия файлов в репозитории |
| `find_campus_place` | Поиск аудиторий и объектов кампуса AITU |

## Тесты

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
