"""Application entry point: validates config and starts the FastAPI server via uvicorn."""

import uvicorn

# Config import triggers env validation — fails loud before any agent runs
# if USE_REAL_IQ=true and OPENAI_API_KEY is missing.
import config  # noqa: F401  (side-effect: env validation)
from observability.otel import configure_otel_providers


def main() -> None:
    """Start the FastAPI server.

    OTel providers are configured here before uvicorn starts so spans are
    available from the very first request.
    """
    # Configure OTel before the ASGI app is loaded — this ensures the global
    # TracerProvider is set before any module-level tracer acquisitions happen.
    configure_otel_providers()

    uvicorn.run(
        "api.server:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
