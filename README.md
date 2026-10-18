# CampusPulse

Помощник студента Astana IT University (AITU). В одном окне объединяет контроль дедлайнов, проверку репозиториев GitHub, составление учебного расписания на неделю и поиск кабинетов по карте кампуса.

Репозиторий проекта: [znaukitai/CampusPulseAI_BadPiggies](https://github.com/znaukitai/CampusPulseAI_BadPiggies)

## Возможности

- **Умный агент:** работает через Google Gemini Function Calling и набор MCP-инструментов (`academic_schedule`, `campus_services`). Если ключ Gemini не задан, автоматически работает встроенный оркестратор MCP-инструментов.
- **Контроль дедлайнов:** расчёт оставшихся дней и приоритетов в часовом поясе `Asia/Almaty`, извлечение дат из текста силлабуса с предпросмотром.
- **Проверка GitHub:** живая проверка статуса репозитория, последних коммитов и наличия обязательных файлов лабораторных работ через GitHub REST API.
- **Карта кампуса AITU:** локальный справочник корпусов C1.1–C1.3 (этажи 1–3) и встроенная интерактивная схема.
- **Светлая и тёмная тема:** минималистичный интерфейс в стиле современных чат-приложений с переключением темы оформления.

## Быстрая установка (через инсталлятор из GitHub Releases) и запуск по exe-файлу

Для пользователей Windows доступна установка без ручной настройки Python и терминала:

1. Перейдите в раздел **[Releases](https://github.com/znaukitai/CampusPulseAI_BadPiggies/releases/latest)** репозитория.
2. Скачайте **`CampusPulse_Setup.exe`** (автоматический установщик) или архив **`CampusPulse-win64.zip`**.
3. Запустите **`CampusPulse_Setup.exe`**:
   - инсталлятор распакует приложение в `%LOCALAPPDATA%\Programs\CampusPulse`,
   - создаст ярлыки **CampusPulse** на Рабочем столе и в меню «Пуск»,
   - запустит `CampusPulse.exe`.
4. При запуске **`CampusPulse.exe`** локальный сервер поднимается автоматически на `http://localhost:8501` и открывается вкладка браузера по умолчанию. Консольное окно лаунчера работает в фоновом режиме — при его закрытии сервер корректно завершает работу.

### Локальная сборка `CampusPulse.exe` и `CampusPulse_Setup.exe`

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts/build_exe.py
```

После сборки исполняемые файлы появятся в `dist/CampusPulse/CampusPulse.exe`, `dist/CampusPulse-win64.zip` и `dist/CampusPulse_Setup.exe`.

## Быстрый старт из исходного кода (Windows)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe launcher.py
```

Или напрямую через Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

После запуска откройте `http://localhost:8501`.

## Настройка `.env`

```dotenv
GEMINI_API_KEY=ваш_ключ
GEMINI_MODEL=gemini-3.8-flash
CAMPUSPULSE_LOCAL_MODE=auto
GITHUB_REPOSITORY=znaukitai/CampusPulseAI_BadPiggies
```

Ключ `GEMINI_API_KEY` и репозиторий также можно указать прямо в боковой панели интерфейса («Подключение и GitHub») — ключ хранится исключительно в памяти текущей сессии.

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

