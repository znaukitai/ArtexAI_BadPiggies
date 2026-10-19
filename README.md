<img src="assets/artex-ai-mark.png" width="48" alt="Artex AI">

# Artex AI

Помощник студента Astana IT University (AITU). В одном окне объединяет контроль дедлайнов, проверку репозиториев GitHub, составление учебного расписания на неделю и поиск кабинетов по карте кампуса.

Репозиторий проекта: [znaukitai/CampusPulseAI_BadPiggies](https://github.com/znaukitai/CampusPulseAI_BadPiggies)

## Возможности

- **Умный агент:** работает через Google Gemini Function Calling и набор MCP-инструментов (`academic_schedule`, `campus_services`). Все вопросы передаются Gemini; инструменты выбираются по смыслу запроса. Для ответов нужен API-ключ или настроенный Cloud Vertex AI.
- **Контроль дедлайнов:** расчёт оставшихся дней и приоритетов в часовом поясе `Asia/Almaty`, извлечение дат из текста силлабуса с предпросмотром.
- **Проверка GitHub:** живая проверка статуса репозитория, последних коммитов и наличия обязательных файлов лабораторных работ через GitHub REST API.
- **Карта кампуса AITU:** локальный справочник корпусов C1.1–C1.3 (этажи 1–3) и встроенная интерактивная схема.
- **Светлая и тёмная тема:** минималистичный интерфейс в стиле современных чат-приложений с переключением темы оформления.

## Быстрая установка (через инсталлятор из GitHub Releases) и запуск по exe-файлу

Версия установщика 1.1.0 скачивает архив последнего релиза и проверяет его SHA-256 по `SHA256SUMS.txt` перед распаковкой. В сборку включены исправления Gemini и обработка произвольных вопросов. Установленный Python не требуется; для ответов нужен ключ Gemini или настроенный Cloud Vertex AI.

Релиз содержит `ArtexAI_Setup.exe` (веб-инсталлер), `ArtexAI-win64.zip` (портативная программа) и `SHA256SUMS.txt`. При наличии Inno Setup в среде сборки также создаётся `ArtexAI_Offline_Setup.exe` — установка без скачивания архива; для Gemini по-прежнему нужен интернет.

После публикации владельцем нового релиза Artex AI установка доступна без Python. Веб-установщик скачивает последний релиз, а не текущую ветку. Старый релиз не содержит эти изменения. Для установки из исходников используйте действующий репозиторий и инструкции ниже:

1. Перейдите в раздел **[Releases](https://github.com/znaukitai/CampusPulseAI_BadPiggies/releases/latest)** репозитория.
2. Скачайте **`ArtexAI_Setup.exe`** (автоматический установщик) или архив **`ArtexAI-win64.zip`**.
3. Запустите **`ArtexAI_Setup.exe`**:
   - инсталлятор распакует приложение в `%LOCALAPPDATA%\Programs\ArtexAI`,
   - создаст ярлыки **Artex AI** на Рабочем столе и в меню «Пуск»,
   - запустит `ArtexAI.exe`.
4. При запуске **`ArtexAI.exe`** локальный сервер поднимается автоматически на `http://localhost:8501` и открывается вкладка браузера по умолчанию. Консольное окно лаунчера работает в фоновом режиме — при его закрытии сервер корректно завершает работу.

### Локальная сборка `ArtexAI.exe` и `ArtexAI_Setup.exe`

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts/build_exe.py
```

После сборки исполняемые файлы появятся в `dist/ArtexAI/ArtexAI.exe`, `dist/ArtexAI-win64.zip` и `dist/ArtexAI_Setup.exe`.

## Установка с нуля на Windows

Требуется 64-битный Python 3.12 (проверено на 3.12.14) и Git. Python 3.15 из старого окружения не используйте. Установите Python 3.12 с python.org.

Действующий репозиторий:

```powershell
git clone --branch artex-update https://github.com/znaukitai/CampusPulseAI_BadPiggies.git
cd CampusPulseAI_BadPiggies
```

При работе с существующим клоном используйте `git fetch origin`, `git switch artex-update`, `git pull --ff-only`. Клонирование ветки доступно после её отправки на GitHub. Название репозитория остаётся прежним, название приложения — Artex AI.

## Создание окружения и запуск

```powershell
py -3.12 -m venv .venv
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
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
GITHUB_REPOSITORY=znaukitai/CampusPulseAI_BadPiggies
```

Ключ `GEMINI_API_KEY` и репозиторий также можно указать прямо в боковой панели интерфейса («Подключение и GitHub») — ключ хранится исключительно в памяти текущей сессии.

## Инструменты MCP

FastMCP описывает инструменты, а агент вызывает их напрямую через локальный мост с Pydantic-валидацией аргументов. Отдельное соединение по MCP-транспорту не используется.

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


## Подключение и диагностика

Получите ключ в [Google AI Studio](https://aistudio.google.com/apikey). Введите его в «Подключение и GitHub» или добавьте значение GEMINI_API_KEY в локальный `.env`. Не отправляйте ключ в чат и не добавляйте `.env` в Git. Поле обычное текстовое с autocomplete=off по требованиям проекта.

Наличие ключа ещё не означает подключение: нажмите «Проверить подключение». Модель из GEMINI_MODEL используется без скрытой подмены. Для проверки вне интерфейса:

```powershell
.venv\Scripts\python.exe scripts/check_gemini.py
.venv\Scripts\python.exe scripts/check_gemini.py --network-check
.venv\Scripts\python.exe scripts/check_gemini.py --list-models
```

Режим `--network-check` проверяет HTTPS без отправки ключа. `ConnectTimeout` означает, что соединение не установлено: сначала проверьте другую сеть или VPN, затем повторите проверку ключа.

401/403 — ключ или доступ; 404 — выберите доступную вашему ключу модель; 429 — лимит; сеть — проверьте соединение, VPN и прокси. Скрипт выводит тип ошибки и безопасное описание, не сырой ответ с потенциальными секретами.

Встроенный ответчик по ключевым словам удалён. Без ключа укажите GEMINI_API_KEY или настройте Cloud Vertex AI. Данные карты и начальные дедлайны помечены DEMO; проверка GitHub использует внешний API. «C1.226», «с1.226», «С1 226», «c1-226» ищутся по всем корпусам, без выдумывания единственного корпуса.

## Обновление и поиск ошибок

```powershell
git pull --ff-only
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe launcher.py --self-test
.venv\Scripts\python.exe -m pytest -q
```

Остановите старый процесс и запустите приложение из обновлённой папки. Если пропала кнопка панели, проверьте `python -m pip show streamlit` (должна быть 1.66.0), URL и порт, затем обновите страницу. Скачанный ранее EXE не обновляется от `git pull`: нужен новый релиз/архив.

Если WinError 10054 повторяется, запишите действие перед ошибкой и безопасный traceback без ключей. Логирование ошибок не отключено. Клиенты Gemini закрываются после запросов; связь конкретного сетевого сброса с браузером/API требует воспроизведения.

Репозиторий сохраняет текущее имя: [адрес и правила обновления](docs/REPOSITORY_RENAME.md).
