"""AI Gateway FastAPI application."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from contentos_ai_gateway.config import settings
from contentos_ai_gateway.routes import embedding, image, providers, speech, subtitle, text, vision


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Central AI routing for ContentOS — text, speech, subtitle, image, vision, embeddings",
        version="0.3.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "ai-gateway", "version": "0.3.0"})

    app.include_router(text.router)
    app.include_router(speech.router)
    app.include_router(subtitle.router)
    app.include_router(image.router)
    app.include_router(vision.router)
    app.include_router(embedding.router)
    app.include_router(providers.router)

    return app


app = create_app()
