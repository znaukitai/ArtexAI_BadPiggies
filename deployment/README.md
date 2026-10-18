# Деплой в Vertex AI Agent Engine

## Требования

Python 3.11+, Google Cloud CLI, проект Google Cloud с включённым Vertex AI API и Cloud Storage bucket.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Настройка `.env`

```dotenv
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_MODEL_LOCATION=global
STAGING_BUCKET=gs://your-staging-bucket
GEMINI_MODEL=gemini-2.5-flash
```

## Авторизация и деплой

```powershell
gcloud auth login
gcloud config set project your-gcp-project-id
gcloud auth application-default login
.\.venv\Scripts\python.exe deployment\deploy.py
```

После успешного деплоя скрипт сохранит имя ресурса в `.deploy/resource_name.txt`. Укажите его в `.env` в поле `AGENT_ENGINE_RESOURCE_NAME`.
