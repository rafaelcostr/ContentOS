from celery import Celery

celery_app = Celery("contentos")
celery_app.config_from_object(
    {
        "broker_url": "redis://redis:6379/0",
        "result_backend": "redis://redis:6379/1",
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_routes": {
            "contentos.trend_intelligence.*": {"queue": "contentos.trend_intelligence"},
            "contentos.research.*": {"queue": "contentos.research"},
            "contentos.hook.*": {"queue": "contentos.hook"},
            "contentos.script.*": {"queue": "contentos.script"},
            "contentos.script_review.*": {"queue": "contentos.script_review"},
            "contentos.emotion.*": {"queue": "contentos.emotion"},
            "contentos.content_score.*": {"queue": "contentos.content_score"},
            "contentos.content_intelligence.*": {"queue": "contentos.content_intelligence"},
            "contentos.scene.*": {"queue": "contentos.scene"},
            "contentos.storyboard.*": {"queue": "contentos.storyboard"},
            "contentos.scene_director.*": {"queue": "contentos.scene_director"},
            "contentos.takes.*": {"queue": "contentos.takes"},
            "contentos.voice.*": {"queue": "contentos.voice"},
            "contentos.subtitle.*": {"queue": "contentos.subtitle"},
            "contentos.editor.*": {"queue": "contentos.editor"},
            "contentos.quality.*": {"queue": "contentos.quality"},
            "contentos.video_review.*": {"queue": "contentos.video_review"},
            "contentos.auto_retry.*": {"queue": "contentos.auto_retry"},
            "contentos.publisher.*": {"queue": "contentos.publisher"},
            "contentos.multi_content.*": {"queue": "contentos.multi_content"},
            "contentos.multi_content_video.*": {"queue": "contentos.multi_content_video"},
            "contentos.clip_research.*": {"queue": "contentos.clip_research"},
            "contentos.asset_collector.*": {"queue": "contentos.asset_collector"},
            "contentos.asset_index.*": {"queue": "contentos.asset_index"},
            "contentos.media_analyze.*": {"queue": "contentos.media_analyze"},
            "contentos.asset_search.*": {"queue": "contentos.asset_search"},
            "contentos.thumbnail.*": {"queue": "contentos.thumbnail"},
            "contentos.analytics.*": {"queue": "contentos.analytics"},
            "contentos.learning.*": {"queue": "contentos.learning"},
            "contentos.knowledge_base.*": {"queue": "contentos.knowledge_base"},
            "contentos.retention.*": {"queue": "contentos.retention"},
            "contentos.seo.*": {"queue": "contentos.seo"},
            "contentos.ai_director.*": {"queue": "contentos.ai_director"},
            "contentos.creative_memory.*": {"queue": "contentos.creative_memory"},
            "contentos.channel_analyzer.*": {"queue": "contentos.channel_analyzer"},
            "contentos.competitor_analyzer.*": {"queue": "contentos.competitor_analyzer"},
            "contentos.content_strategist.*": {"queue": "contentos.content_strategist"},
            "contentos.workflow.*": {"queue": "contentos.workflow"},
        },
        "task_default_queue": "contentos.workflow",
    }
)


def dispatch_agent_task(
    queue: str,
    job_id: str,
    pipeline_id: str,
    project_id: str,
    step: str,
    payload: dict,
    countdown: int = 0,
) -> str:
    """Dispatch task to agent queue. Returns Celery task ID."""
    from contentos_shared.telemetry import celery_trace_carrier

    kwargs: dict = {
        "job_id": job_id,
        "pipeline_id": pipeline_id,
        "project_id": project_id,
        "step": step,
        "payload": payload,
    }
    carrier = celery_trace_carrier()
    if carrier:
        kwargs["_trace_carrier"] = carrier

    result = celery_app.send_task(
        f"contentos.{step}.execute",
        kwargs=kwargs,
        queue=queue,
        countdown=countdown,
    )
    return result.id


def dispatch_async_agent(
    step: str,
    pipeline_id: str,
    project_id: str,
    payload: dict,
) -> str:
    """Fire-and-forget V2 async agent (thumbnail, analytics) — no workflow job."""
    import uuid

    queue = f"contentos.{step}"
    job_id = str(uuid.uuid4())
    from contentos_shared.telemetry import celery_trace_carrier

    kwargs: dict = {
        "job_id": job_id,
        "pipeline_id": pipeline_id,
        "project_id": project_id,
        "step": step,
        "payload": payload,
        "async_mode": True,
    }
    carrier = celery_trace_carrier()
    if carrier:
        kwargs["_trace_carrier"] = carrier

    result = celery_app.send_task(
        f"contentos.{step}.execute",
        kwargs=kwargs,
        queue=queue,
    )
    return result.id
