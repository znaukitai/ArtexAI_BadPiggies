"""Check Gemini outside Streamlit. Secrets stay in memory and never print."""
import os
import sys
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from google import genai
from core.input_normalization import normalize_api_key
from agent.artex_agent import DEFAULT_GEMINI_MODEL, _classify_api_error


def main() -> int:
    load_dotenv(ROOT / ".env")
    if "--network-check" in sys.argv:
        print("Проверка HTTPS до сервера Gemini без отправки API-ключа.")
        try:
            with httpx.Client(timeout=httpx.Timeout(15, connect=10)) as client:
                response = client.get("https://generativelanguage.googleapis.com/v1beta/models")
            print(f"HTTP {response.status_code}: HTTPS-соединение установлено. Отказ без ключа ожидаем.")
            return 0
        except httpx.RequestError as exc:
            print(f"{type(exc).__name__}: {_classify_api_error(exc, DEFAULT_GEMINI_MODEL)}")
            return 1
    key = normalize_api_key(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if not key:
        print("Ключ не указан. Укажите GEMINI_API_KEY в локальном .env.")
        return 2
    model = os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    try:
        with genai.Client(api_key=key, http_options={"timeout": 10000}) as client:
            if "--list-models" in sys.argv:
                for entry in client.models.list():
                    print(entry.name)
            else:
                client.models.generate_content(model=model, contents="Reply OK", config={"max_output_tokens": 8, "automatic_function_calling": {"disable": True}})
                print(f"Gemini подключён ({model}).")
        return 0
    except Exception as exc:
        # Exception bodies may contain request URLs/credentials: print a safe classification.
        print(f"{type(exc).__name__}: {_classify_api_error(exc, model)}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
