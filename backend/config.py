"""Application configuration: reads environment variables and validates required values on startup."""

import os
from dotenv import load_dotenv

# Load .env file if present (no-op in production where vars are injected directly)
load_dotenv()


def _require_env(name: str) -> str:
    """Return the value of an environment variable or raise ValueError if missing."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(
            f"Required environment variable '{name}' is not set. "
            "Set it in your .env file or export it before starting the server."
        )
    return value


# ---------------------------------------------------------------------------
# IQ provider mode
# ---------------------------------------------------------------------------
USE_REAL_IQ: bool = os.environ.get("USE_REAL_IQ", "false").strip().lower() == "true"

# ---------------------------------------------------------------------------
# Azure AI Foundry — read natively by FoundryChatClient
# FOUNDRY_PROJECT_ENDPOINT: your Foundry project endpoint
#   e.g. https://<hub>.services.ai.azure.com/api/projects/<project>
# FOUNDRY_MODEL: the model deployment name inside the project
#   e.g. gpt-4o, gpt-4o-mini
# Authentication: DefaultAzureCredential (az login / managed identity — no API key)
# ---------------------------------------------------------------------------
FOUNDRY_PROJECT_ENDPOINT: str = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
FOUNDRY_MODEL: str = os.environ.get("FOUNDRY_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# OpenTelemetry
# ---------------------------------------------------------------------------
OTEL_EXPORTER_OTLP_ENDPOINT: str = os.environ.get(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_SERVICE_NAME: str = os.environ.get(
    "OTEL_SERVICE_NAME", "enterprise-learning-system"
)

# ---------------------------------------------------------------------------
# FastAPI server
# ---------------------------------------------------------------------------
APP_HOST: str = os.environ.get("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.environ.get("APP_PORT", "8000"))

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
FRONTEND_ORIGIN: str = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
CHROMA_EF_MODEL: str = os.environ.get("CHROMA_EF_MODEL", "")

# ---------------------------------------------------------------------------
# Foundry IQ Knowledge Base
# ---------------------------------------------------------------------------
AZURE_SEARCH_ENDPOINT: str = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_API_KEY: str = os.environ.get("AZURE_SEARCH_API_KEY", "")
FOUNDRY_IQ_KB_NAME: str = os.environ.get("FOUNDRY_IQ_KB_NAME", "")
FOUNDRY_IQ_RETRIEVAL_MODE: str = os.environ.get("FOUNDRY_IQ_RETRIEVAL_MODE", "semantic")
FOUNDRY_IQ_REASONING_EFFORT: str = os.environ.get("FOUNDRY_IQ_REASONING_EFFORT", "minimal")
FOUNDRY_IQ_OUTPUT_MODE: str = os.environ.get("FOUNDRY_IQ_OUTPUT_MODE", "extractive_data")
