"""Agency clients (step 3a of the client-service build plan): clients, their codebases and jobs.

Separate from the SaaS Customer Portal's organisations: these are businesses whose existing code we
take over and support (Health Check -> Audit -> fixes/upgrades -> care plan).
"""
from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformClient(PlatformBase):
    __tablename__ = "platform_clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    contact = Column(String, nullable=True)  # email or Upwork handle, as the founder enters it
    notes = Column(Text, default="", nullable=False)
    status = Column(String, default="lead", index=True, nullable=False)  # lead | active | past
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformClientCodebase(PlatformBase):
    __tablename__ = "platform_client_codebases"

    id = Column(Integer, primary_key=True, index=True)
    codebase_id = Column(String, unique=True, index=True, nullable=False)
    client_id = Column(String, index=True, nullable=False)
    label = Column(String, nullable=False)
    source_kind = Column(String, nullable=False)  # git_url | local_folder
    source = Column(String, nullable=False)  # https URL (no credentials) or absolute folder path
    local_path = Column(String, nullable=True)  # where the read-only copy lives
    status = Column(String, default="added", index=True, nullable=False)  # added | fetching | ready | checking | failed
    error = Column(Text, nullable=True)
    last_check_json = Column(Text, nullable=True)  # Health Check summary (grade, scores, top risks)
    last_report_path = Column(String, nullable=True)  # PDF on this machine
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformClientJob(PlatformBase):
    __tablename__ = "platform_client_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    client_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    kind = Column(String, default="fix", nullable=False)  # health_check | audit | fix | feature | upgrade | care_plan
    status = Column(String, default="lead", index=True, nullable=False)  # lead | quoted | in_progress | delivered | paid | closed
    price = Column(String, nullable=True)  # free text, e.g. "$99 fixed" or "$300/month"
    notes = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlatformClientWork(PlatformBase):
    """A job handed to the AI team (step 4a): one Orca mission on a disposable copy of one codebase."""
    __tablename__ = "platform_client_work"

    id = Column(Integer, primary_key=True, index=True)
    work_id = Column(String, unique=True, index=True, nullable=False)
    job_id = Column(String, index=True, nullable=False)
    client_id = Column(String, index=True, nullable=False)
    codebase_id = Column(String, nullable=False)
    mission_id = Column(String, index=True, nullable=False)
    workspace = Column(String, nullable=False)  # the mission's copy of the code
    git_dir = Column(String, nullable=False)  # its history, kept outside the copy (baseline commit)
    ai_provider = Column(String, nullable=False)  # who read the client's code, as confirmed by the founder
    consent_by = Column(String, nullable=False)  # founder who confirmed the client agreed
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
