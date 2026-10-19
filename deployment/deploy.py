"""Deploy ArtexAgent to Vertex AI Agent Engine."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.artex_agent import ArtexAgent

DEPLOY_RECORD_PATH = PROJECT_ROOT / ".deploy" / "resource_name.txt"

CLOUD_REQUIREMENTS = [
    "pydantic==2.14.1",
    "google-genai==1.75.0",
    "google-cloud-aiplatform[agent_engines,reasoningengine]>=1.79.0",
    "mcp>=1.3.0",
    "fastmcp>=0.4.1",
    "httpx==0.28.1",
    "cloudpickle==3.1.1",
    "tzdata==2025.1",
]

EXTRA_PACKAGES = [
    "agent",
    "core",
    "mcp_servers",
    "data",
]


def _get_env_or_fail(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default or "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Check deployment/README.md for configuration instructions."
        )
    return val


def deploy_agent(skip_smoke_test: bool = False) -> str:
    """Package and deploy ArtexAgent to Vertex AI Agent Engine."""
    import vertexai

    project_id = _get_env_or_fail("GOOGLE_CLOUD_PROJECT")
    location = _get_env_or_fail("GOOGLE_CLOUD_LOCATION", "us-central1")
    staging_bucket = _get_env_or_fail("STAGING_BUCKET")
    model_name = _get_env_or_fail("GEMINI_MODEL", "gemini-2.5-flash")

    if not staging_bucket.startswith("gs://"):
        staging_bucket = f"gs://{staging_bucket}"

    print(f"[DEPLOY] Initializing Vertex AI (project={project_id}, location={location}, bucket={staging_bucket})")
    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    local_agent = ArtexAgent(
        model=model_name,
        project=project_id,
        location=location,
        model_location=os.environ.get("GOOGLE_CLOUD_MODEL_LOCATION", "global"),
        max_steps=6,
    )

    display_name = "artex-agent"
    description = "Artex AI: student assistant for Astana IT University"

    remote_agent: Any = None
    if hasattr(vertexai, "agent_engines"):
        print("[DEPLOY] Deploying via vertexai.agent_engines.create()...")
        remote_agent = vertexai.agent_engines.create(
            agent_engine=local_agent,
            requirements=CLOUD_REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            display_name=display_name,
            description=description,
        )
    else:
        from vertexai.preview import reasoning_engines

        print("[DEPLOY] Deploying via reasoning_engines.ReasoningEngine.create()...")
        remote_agent = reasoning_engines.ReasoningEngine.create(
            reasoning_engine=local_agent,
            requirements=CLOUD_REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            display_name=display_name,
            description=description,
        )

    resource_name = str(getattr(remote_agent, "resource_name", ""))
    if not resource_name:
        raise RuntimeError("Deployment succeeded but resource_name was empty.")

    DEPLOY_RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_RECORD_PATH.write_text(resource_name + "\n", encoding="utf-8")
    print(f"[DEPLOY] Resource name saved to {DEPLOY_RECORD_PATH}: {resource_name}")

    if not skip_smoke_test:
        print("[SMOKE TEST] Running remote query...")
        smoke_response = remote_agent.query(
            user_input="Какое сегодня число в Астане? Вызови get_today."
        )
        print(f"  Answer     : {smoke_response.get('answer')}")
        print(f"  Steps count: {smoke_response.get('meta', {}).get('steps_count')}")
        print(f"  Tool calls : {smoke_response.get('meta', {}).get('tool_calls')}")

    return resource_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy ArtexAgent to Vertex AI.")
    parser.add_argument(
        "--skip-smoke-test",
        action="store_true",
        help="Skip running the post-deployment query smoke test.",
    )
    args = parser.parse_args()
    deploy_agent(skip_smoke_test=args.skip_smoke_test)


if __name__ == "__main__":
    main()
