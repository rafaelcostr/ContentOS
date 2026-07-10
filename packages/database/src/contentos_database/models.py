import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class ContentBatchStatus(str, enum.Enum):
  PLANNED = "planned"
  RUNNING = "running"
  PENDING_PUBLISH_APPROVAL = "pending_publish_approval"
  COMPLETED = "completed"
  CANCELLED = "cancelled"
  FAILED = "failed"


class PipelineStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.EDITOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    org_memberships: Mapped[list["OrganizationMember"]] = relationship(back_populates="user")


class Organization(Base):
    """Tenant workspace (V3 Tier C1)."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")
    api_keys: Mapped[list["OrganizationApiKey"]] = relationship(back_populates="organization")
    billing: Mapped["OrganizationBilling | None"] = relationship(back_populates="organization", uselist=False)


class SubscriptionStatus(str, enum.Enum):
    NONE = "none"
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class BillingPlan(Base):
    """Catalog of subscription plans (V3 Tier C3)."""

    __tablename__ = "billing_plans"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    monthly_credits: Mapped[int] = mapped_column(Integer, default=50)
    monthly_pipeline_quota: Mapped[int] = mapped_column(Integer, default=20)
    max_concurrent_pipelines: Mapped[int] = mapped_column(Integer, default=1)
    price_usd_cents: Mapped[int | None] = mapped_column(Integer)
    stripe_price_id: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subscriptions: Mapped[list["OrganizationBilling"]] = relationship(back_populates="plan")


class OrganizationBilling(Base):
    """Stripe subscription + credit balance per organization."""

    __tablename__ = "organization_billing"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    plan_slug: Mapped[str] = mapped_column(ForeignKey("billing_plans.slug"), default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120), index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120), index=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.NONE
    )
    credits_balance: Mapped[int] = mapped_column(Integer, default=0)
    credits_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="billing")
    plan: Mapped["BillingPlan"] = relationship(back_populates="subscriptions")


class CreditTransaction(Base):
    """Immutable credit ledger entry."""

    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    reference_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiKeyScope(str, enum.Enum):
    READ = "read"
    WRITE = "write"


class OrganizationApiKey(Base):
    """Public API key scoped to an organization (V3 Tier C5)."""

    __tablename__ = "organization_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    key_prefix: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(64))
    scope: Mapped[ApiKeyScope] = mapped_column(Enum(ApiKeyScope), default=ApiKeyScope.READ)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=120)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["Organization"] = relationship(back_populates="api_keys")


class OrganizationMember(Base):
    """User membership in an organization with org-scoped role."""

    __tablename__ = "organization_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.EDITOR)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="org_memberships")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped["User"] = relationship(back_populates="projects")
    organization: Mapped["Organization | None"] = relationship(back_populates="projects")
    pipelines: Mapped[list["Pipeline"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    videos: Mapped[list["Video"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    memory: Mapped["ProjectMemory | None"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    schedules: Mapped[list["PipelineSchedule"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    content_batches: Mapped[list["ContentBatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ContentBatch(Base):
    """N pipelines per topic — Content Factory (V5.3)."""

    __tablename__ = "content_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(500))
    workflow_name: Mapped[str | None] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ContentBatchStatus] = mapped_column(Enum(ContentBatchStatus), default=ContentBatchStatus.PLANNED)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    variants: Mapped[list | None] = mapped_column(JSON)
    estimated_credit_cost: Mapped[int] = mapped_column(Integer, default=0)
    publish_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="content_batches")


class PipelineSchedule(Base):
    """Cron-based pipeline trigger per project (V3 Tier D1)."""

    __tablename__ = "pipeline_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    topic: Mapped[str] = mapped_column(String(500))
    workflow_name: Mapped[str | None] = mapped_column(String(80))
    cron_expression: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_pipeline_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    context_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="schedules")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(500))
    workflow_name: Mapped[str | None] = mapped_column(String(80), index=True)
    status: Mapped[PipelineStatus] = mapped_column(Enum(PipelineStatus), default=PipelineStatus.PENDING)
    current_step: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    context_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="pipelines")
    jobs: Mapped[list["Job"]] = relationship(back_populates="pipeline", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    step: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    order: Mapped[int] = mapped_column(Integer, default=0)
    input_data: Mapped[dict | None] = mapped_column(JSON)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="jobs")
    logs: Mapped[list["LogEntry"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int] = mapped_column(Integer, default=1080)
    height: Mapped[int] = mapped_column(Integer, default=1920)
    fps: Mapped[int] = mapped_column(Integer, default=60)
    render_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    thumb_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    hashtags: Mapped[list | None] = mapped_column(JSON)
    platform_variants: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="videos")


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500))
    hook: Mapped[str] = mapped_column(Text)
    development: Mapped[str] = mapped_column(Text)
    curiosity: Mapped[str] = mapped_column(Text)
    call_to_action: Mapped[str] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=45)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    script_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scripts.id", ondelete="SET NULL"))
    order: Mapped[int] = mapped_column(Integer)
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    visual_hint: Mapped[str | None] = mapped_column(String(500))
    take_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(String(50), index=True)
    bucket: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(1000))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    tags: Mapped[list | None] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssetMediaProfile(Base):
    """V5.0.3 — vision analysis and semantic embedding per video asset."""

    __tablename__ = "asset_media_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), unique=True, index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    analysis: Mapped[dict | None] = mapped_column(JSON)
    embedding: Mapped[list | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    vision_model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class VoiceProfile(Base):
    """V5.1.1 — reusable narration settings (speed, pitch, pause)."""

    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str] = mapped_column(String(50), default="piper")
    voice_id: Mapped[str | None] = mapped_column(String(120))
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    pitch_semitones: Mapped[float] = mapped_column(Float, default=0.0)
    pause_ms: Mapped[int] = mapped_column(Integer, default=300)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Audio(Base):
    __tablename__ = "audio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50), default="elevenlabs")
    voice_id: Mapped[str | None] = mapped_column(String(100))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subtitle(Base):
    __tablename__ = "subtitles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    srt_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    json_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    language: Mapped[str] = mapped_column(String(10), default="pt")
    segments: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LogEntry(Base):
    __tablename__ = "logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(20), default="info")
    agent: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["Job | None"] = relationship(back_populates="logs")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    credentials: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))
    content: Mapped[dict] = mapped_column(JSON)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Analytics(Base):
    __tablename__ = "analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    metric: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    dimensions: Mapped[dict | None] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlatformAnalyticsSnapshot(Base):
    """OAuth platform metrics snapshot — V5.4.1."""

    __tablename__ = "platform_analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    external_media_id: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    metrics: Mapped[dict] = mapped_column(JSON)
    channel_totals: Mapped[dict | None] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class DeadLetterJob(Base):
    __tablename__ = "dead_letter_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    step: Mapped[str] = mapped_column(String(50))
    error_message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProviderConfig(Base):
    """Registered AI/media provider — configurable without code changes."""

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    provider_type: Mapped[str] = mapped_column(String(50), index=True)  # text | speech | subtitle
    implementation: Mapped[str] = mapped_column(String(100))  # ollama | piper | local | openai
    config: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentModelSetting(Base):
    """Per-agent provider and model configuration (Model Manager V2.3)."""

    __tablename__ = "agent_model_configs"

    agent: Mapped[str] = mapped_column(String(50), primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(20))  # text | speech | subtitle | compute
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProjectMemory(Base):
    """Per-project creative memory (Memory Manager V2.4)."""

    __tablename__ = "project_memory"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    tone: Mapped[str | None] = mapped_column(String(255))
    vocabulary: Mapped[list | None] = mapped_column(JSON)
    cta: Mapped[str | None] = mapped_column(String(500))
    avg_duration: Mapped[float | None] = mapped_column(Float)
    hook_style: Mapped[str | None] = mapped_column(String(255))
    niche: Mapped[str | None] = mapped_column(String(255))
    goal: Mapped[str | None] = mapped_column(String(500))
    style: Mapped[dict | None] = mapped_column(JSON)
    history: Mapped[list | None] = mapped_column(JSON)
    # V4 Project DNA (Epic 8)
    humor_level: Mapped[float | None] = mapped_column(Float)
    pace: Mapped[str | None] = mapped_column(String(20))
    visual_style: Mapped[dict | None] = mapped_column(JSON)
    narrator_persona: Mapped[str | None] = mapped_column(String(255))
    preferred_formats: Mapped[list | None] = mapped_column(JSON)
    hook_patterns: Mapped[list | None] = mapped_column(JSON)
    cta_style: Mapped[str | None] = mapped_column(String(255))
    default_voice_builtin: Mapped[str | None] = mapped_column(String(80))
    # V5.1.4 Project DNA 2.0
    cinematic_preset: Mapped[str | None] = mapped_column(String(40))
    content_angle: Mapped[str | None] = mapped_column(String(40))
    brand_keywords: Mapped[list | None] = mapped_column(JSON)
    editing_preferences: Mapped[dict | None] = mapped_column(JSON)
    # Growth OS Fase 5 — Brand Intelligence (extends DNA, same row)
    mission: Mapped[str | None] = mapped_column(Text)
    objectives: Mapped[list | None] = mapped_column(JSON)
    values: Mapped[list | None] = mapped_column(JSON)
    target_audience: Mapped[str | None] = mapped_column(String(500))
    editorial_rules: Mapped[list | None] = mapped_column(JSON)
    color_palette: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="memory")


class CostEntry(Base):
    """AI operation cost record (Cost Manager V2.6)."""

    __tablename__ = "cost_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), index=True)
    agent: Mapped[str] = mapped_column(String(50), index=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    model: Mapped[str] = mapped_column(String(120))
    operation: Mapped[str] = mapped_column(String(50), default="text_chat")
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DomainEventRecord(Base):
    """Persisted domain events (Event Bus V2.7)."""

    __tablename__ = "domain_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), index=True)
    agent: Mapped[str | None] = mapped_column(String(50), index=True)
    step: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(30))
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AnalyticsInsight(Base):
    """AI-generated post-publication analysis (V2.8)."""

    __tablename__ = "analytics_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), unique=True, index=True)
    video_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("videos.id", ondelete="SET NULL"))
    metrics: Mapped[dict | None] = mapped_column(JSON)
    analysis: Mapped[dict | None] = mapped_column(JSON)
    models_used: Mapped[dict | None] = mapped_column(JSON)
    prompts_used: Mapped[dict | None] = mapped_column(JSON)
    applied_to_memory: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class InstalledPlugin(Base):
    """Plugin marketplace install state (V2.9)."""

    __tablename__ = "installed_plugins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(30), default="marketplace")
    manifest: Mapped[dict | None] = mapped_column(JSON)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PipelineAssetCollection(Base):
    """V2 clip research + asset collector results per pipeline."""

    __tablename__ = "pipeline_asset_collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), unique=True, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    candidates: Mapped[list | None] = mapped_column(JSON)
    assets: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkflowDefinition(Base):
    """Pipeline template — steps and configuration."""

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    slug: Mapped[str | None] = mapped_column(String(80), index=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    steps: Mapped[list] = mapped_column(JSON)  # ordered step names
    config: Mapped[dict | None] = mapped_column(JSON)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AbVariantRow(Base):
    """V4 A/B Testing — persisted variant sets per pipeline dimension (Epic 6)."""

    __tablename__ = "ab_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), index=True)
    dimension: Mapped[str] = mapped_column(String(50), index=True)
    variants: Mapped[list] = mapped_column(JSON)
    winner_index: Mapped[int] = mapped_column(Integer, default=0)
    winner: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MultiContentArtifactRow(Base):
    """V4 Multi Content — text artifacts per pipeline format (Epic 2a)."""

    __tablename__ = "multi_content_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), index=True)
    format: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    content_text: Mapped[str] = mapped_column(Text, default="")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    source: Mapped[str] = mapped_column(String(30), default="heuristic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class VideoPlatformVariantRow(Base):
    """V4 Multi Content Video — per-platform metadata and crop specs (Epic 2b)."""

    __tablename__ = "video_platform_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list | None] = mapped_column(JSON)
    crop_spec: Mapped[dict | None] = mapped_column(JSON)
    render_ref: Mapped[dict | None] = mapped_column(JSON)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    source: Mapped[str] = mapped_column(String(30), default="heuristic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PerformanceLearningRow(Base):
    """V5.4.2 — OAuth performance insights (CTR, retention) → learning."""

    __tablename__ = "performance_learning_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    external_media_id: Mapped[str | None] = mapped_column(String(120), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    topic: Mapped[str] = mapped_column(String(500), default="")
    ctr: Mapped[float | None] = mapped_column(Float)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    retention_pct: Mapped[float | None] = mapped_column(Float)
    retention_delta: Mapped[float | None] = mapped_column(Float)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    performance_tier: Mapped[str] = mapped_column(String(20), default="medium")
    learnings: Mapped[list | None] = mapped_column(JSON)
    kb_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class CommentAnalysisRow(Base):
    """V5.4.3 — comment sentiment/themes per published media."""

    __tablename__ = "comment_analysis_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    external_media_id: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_pct: Mapped[float] = mapped_column(Float, default=0.0)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0)
    neutral_pct: Mapped[float] = mapped_column(Float, default=0.0)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    themes: Mapped[list | None] = mapped_column(JSON)
    sample_comments: Mapped[list | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(300))
    kb_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class CommunityReplyDraftRow(Base):
    """V5.4.4 — community reply drafts (human approval, no auto-post)."""

    __tablename__ = "community_reply_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    external_media_id: Mapped[str | None] = mapped_column(String(120), index=True)
    media_title: Mapped[str | None] = mapped_column(String(500))
    original_comment: Mapped[str] = mapped_column(Text)
    comment_author: Mapped[str | None] = mapped_column(String(255))
    draft_reply: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="general")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LearningInsightRow(Base):
    """V4 Learning Engine — post-pipeline insights (Epic 7)."""

    __tablename__ = "learning_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), index=True, unique=True)
    topic: Mapped[str] = mapped_column(String(500), default="")
    content_score: Mapped[float | None] = mapped_column(Float)
    viral_score: Mapped[float | None] = mapped_column(Float)
    specialist_id: Mapped[str | None] = mapped_column(String(100))
    hook_text: Mapped[str] = mapped_column(Text, default="")
    cta_text: Mapped[str] = mapped_column(Text, default="")
    signals: Mapped[list | None] = mapped_column(JSON)
    memory_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    memory_updates: Mapped[list | None] = mapped_column(JSON)
    kb_indexed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class TrendForecastRow(Base):
    """V4 Trend Forecast — persisted scores per pipeline (Epic 10)."""

    __tablename__ = "trend_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), index=True, unique=True)
    topic: Mapped[str] = mapped_column(String(500), default="")
    niche: Mapped[str] = mapped_column(String(200), default="")
    trend_score: Mapped[float] = mapped_column(Float, default=50.0)
    expected_growth: Mapped[str] = mapped_column(String(30), default="moderate")
    production_recommendation: Mapped[str] = mapped_column(Text, default="")
    report: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ContentRelationRow(Base):
    """V4 Content Relation Graph — directed edges between content nodes (Epic 11)."""

    __tablename__ = "content_relations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str] = mapped_column(String(120), index=True)
    relation_type: Mapped[str] = mapped_column(String(50), index=True)
    label_source: Mapped[str] = mapped_column(String(500), default="")
    label_target: Mapped[str] = mapped_column(String(500), default="")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class KnowledgeEntry(Base):
    """V4 Knowledge Base — indexed content with optional embeddings (Epic 3)."""

    __tablename__ = "knowledge_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"), index=True)
    resource_type: Mapped[str] = mapped_column(String(50), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    content_text: Mapped[str] = mapped_column(Text, default="")
    snippet: Mapped[str] = mapped_column(String(1000), default="")
    embedding: Mapped[list | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_entries.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PlatformPublicationRow(Base):
    """Audit log for publisher attempts per platform (phase 6)."""

    __tablename__ = "platform_publications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipelines.id", ondelete="SET NULL"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    publish_mode: Mapped[str] = mapped_column(String(30), default="dry_run", index=True)
    status: Mapped[str] = mapped_column(String(40), default="ready", index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    external_id: Mapped[str | None] = mapped_column(String(200), index=True)
    publish_url: Mapped[str | None] = mapped_column(String(1000))
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class GrowthChannelProfileRow(Base):
    """Growth profile data attached to an existing channel."""

    __tablename__ = "growth_channel_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), index=True, unique=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    profile_data: Mapped[dict | None] = mapped_column(JSON)
    report: Mapped[dict | None] = mapped_column(JSON)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChannelMemoryRow(Base):
    """Per-channel creative patterns — Growth OS Fase 6."""

    __tablename__ = "channel_memory"

    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    winning_videos: Mapped[list | None] = mapped_column(JSON)
    losing_videos: Mapped[list | None] = mapped_column(JSON)
    top_hooks: Mapped[list | None] = mapped_column(JSON)
    top_ctas: Mapped[list | None] = mapped_column(JSON)
    top_themes: Mapped[list | None] = mapped_column(JSON)
    top_hashtags: Mapped[list | None] = mapped_column(JSON)
    best_posting_hours: Mapped[list | None] = mapped_column(JSON)
    insights: Mapped[list | None] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GrowthCompetitorRow(Base):
    """Competitor profile tracked by Growth AI."""

    __tablename__ = "growth_competitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    handle: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GrowthReportRow(Base):
    """Persisted Growth AI report snapshot."""

    __tablename__ = "growth_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")
    report: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class GrowthStrategyRow(Base):
    """Growth strategy draft or active plan."""

    __tablename__ = "growth_strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    goals: Mapped[list | None] = mapped_column(JSON)
    kpis: Mapped[dict | None] = mapped_column(JSON)
    cadence: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GrowthRecommendationRow(Base):
    """Actionable Growth AI recommendation."""

    __tablename__ = "growth_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(30), default="medium", index=True)
    source: Mapped[str] = mapped_column(String(80), default="growth", index=True)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class GrowthAssetPerformanceRow(Base):
    """Growth performance aggregation for a media asset."""

    __tablename__ = "growth_asset_performance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float | None] = mapped_column(Float)
    retention_pct: Mapped[float | None] = mapped_column(Float)
    watch_time_seconds: Mapped[float | None] = mapped_column(Float)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    ai_score: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True)


class GrowthContentCalendarRow(Base):
    """Growth content calendar item."""

    __tablename__ = "growth_content_calendar"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    topic: Mapped[str] = mapped_column(String(500), default="")
    planned_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(40), default="planned", index=True)
    metadata_: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
