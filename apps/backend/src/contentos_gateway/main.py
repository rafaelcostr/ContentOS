"""ContentOS API Gateway — authentication, routing, WebSocket hub."""

import asyncio
from contextlib import asynccontextmanager, suppress

from contentos_database.session import create_tables, init_db
from contentos_gateway.api.routes import (
    ab_variants,
    agents,
    analytics,
    api_keys,
    assets,
    auth,
    billing,
    cache,
    channel_memory,
    channels,
    comment_analyzer,
    community,
    content_score,
    content_sources,
    costs,
    creative_memory,
    director,
    events,
    executive,
    factory,
    graph,
    growth,
    health,
    jobs,
    knowledge,
    learning,
    logs,
    marketplace,
    memory,
    metrics,
    models,
    multi_content,
    oauth,
    ops,
    organizations,
    performance_learning,
    pipelines,
    platform_analytics,
    platform_channel,
    platform_plugins,
    project_brand,
    project_dna,
    projects,
    prometheus,
    prompts,
    providers,
    publish,
    retention,
    reuse,
    schedules,
    seo,
    specialists,
    trend,
    videos,
    viral,
    voice_library,
    voice_profiles,
    workflow_builder,
    youtube_channel,
)
from contentos_gateway.api.websocket import router as ws_router
from contentos_gateway.config import settings
from contentos_gateway.middleware.hardening import GatewayHardeningMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


async def _scheduler_loop() -> None:
    from contentos_database.scheduler_service import (
        run_due_schedules,
        scheduler_enabled,
        scheduler_interval_seconds,
    )

    if not scheduler_enabled():
        return
    interval = scheduler_interval_seconds()
    while True:
        await asyncio.sleep(interval)
        try:
            from contentos_database.session import get_session_factory

            session_factory = get_session_factory()
            if not session_factory:
                continue
            async with session_factory() as db:
                await run_due_schedules(db, settings.workflow_engine_url)
                await db.commit()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    from contentos_shared.telemetry import init_telemetry, instrument_fastapi, shutdown_telemetry

    init_telemetry("contentos-gateway")
    instrument_fastapi(app)
    init_db(settings.database_url, echo=settings.debug)
    await create_tables()
    try:
        from contentos_intelligence.application.bootstrap import configure_intelligence_registry

        configure_intelligence_registry(with_database=True)
    except Exception:
        pass
    scheduler_task: asyncio.Task | None = None
    try:
        from contentos_database.session import get_session_factory
        from contentos_models import get_model_manager

        session_factory = get_session_factory()
        if session_factory:
            async with session_factory() as db:
                await get_model_manager().ensure_defaults(db)
                from contentos_database.workflow_seed import ensure_workflow_templates

                await ensure_workflow_templates(db)
                from contentos_database.org_seed import backfill_organizations

                await backfill_organizations(db)
                from contentos_database.billing_seed import backfill_org_billing, ensure_billing_plans

                await ensure_billing_plans(db)
                await backfill_org_billing(db)
                await db.commit()
    except Exception:
        pass
    scheduler_task = asyncio.create_task(_scheduler_loop())
    yield
    if scheduler_task:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task
    shutdown_telemetry()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ContentOS API Gateway",
        description="Gateway for ContentOS SaaS — auth, projects, jobs, assets",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GatewayHardeningMiddleware)

    prefix = "/api/v1"
    app.include_router(prometheus.router)
    app.include_router(health.router)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(organizations.router, prefix=prefix)
    app.include_router(api_keys.router, prefix=prefix)
    app.include_router(billing.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(schedules.router, prefix=prefix)
    app.include_router(memory.router, prefix=prefix)
    app.include_router(project_dna.router, prefix=prefix)
    app.include_router(project_brand.router, prefix=prefix)
    app.include_router(knowledge.router, prefix=prefix)
    app.include_router(reuse.router, prefix=prefix)
    app.include_router(viral.router, prefix=prefix)
    app.include_router(ab_variants.router, prefix=prefix)
    app.include_router(content_score.router, prefix=prefix)
    app.include_router(retention.router, prefix=prefix)
    app.include_router(seo.router, prefix=prefix)
    app.include_router(director.router, prefix=prefix)
    app.include_router(creative_memory.router, prefix=prefix)
    app.include_router(factory.router, prefix=prefix)
    app.include_router(specialists.router, prefix=prefix)
    app.include_router(multi_content.router, prefix=prefix)
    app.include_router(learning.router, prefix=prefix)
    app.include_router(performance_learning.router, prefix=prefix)
    app.include_router(trend.router, prefix=prefix)
    app.include_router(graph.router, prefix=prefix)
    app.include_router(growth.router, prefix=prefix)
    app.include_router(executive.router, prefix=prefix)
    app.include_router(ops.router, prefix=prefix)
    app.include_router(pipelines.router, prefix=prefix)
    app.include_router(jobs.router, prefix=prefix)
    app.include_router(assets.router, prefix=prefix)
    app.include_router(voice_profiles.router, prefix=prefix)
    app.include_router(voice_library.router, prefix=prefix)
    app.include_router(analytics.router, prefix=prefix)
    app.include_router(platform_analytics.router, prefix=prefix)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(videos.router, prefix=prefix)
    app.include_router(logs.router, prefix=prefix)
    app.include_router(providers.router, prefix=prefix)
    app.include_router(prompts.router, prefix=prefix)
    app.include_router(models.router, prefix=prefix)
    app.include_router(cache.router, prefix=prefix)
    app.include_router(costs.router, prefix=prefix)
    app.include_router(content_sources.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(metrics.router, prefix=prefix)
    app.include_router(platform_plugins.router, prefix=prefix)
    app.include_router(marketplace.router, prefix=prefix)
    app.include_router(workflow_builder.router, prefix=prefix)
    app.include_router(channels.router, prefix=prefix)
    app.include_router(channel_memory.router, prefix=prefix)
    app.include_router(youtube_channel.router, prefix=prefix)
    app.include_router(platform_channel.router, prefix=prefix)
    app.include_router(comment_analyzer.router, prefix=prefix)
    app.include_router(community.router, prefix=prefix)
    app.include_router(oauth.router, prefix=prefix)
    app.include_router(publish.router, prefix=prefix)
    app.include_router(ws_router)

    return app


app = create_app()
