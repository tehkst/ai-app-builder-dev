from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformUiUxProposal(PlatformBase):
    """A founder-facing UI/UX change proposal: SOW + candidate edit + Digital Twin preview.

    Never applied to the real target file until approve_ui_change dispatches the
    existing governed github_execution PR-creation flow - this table only tracks the
    proposal/preview lifecycle, not a code-execution surface.
    """

    __tablename__ = "platform_ui_ux_proposals"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String, unique=True, index=True, nullable=False)
    conversation_id = Column(String, index=True, nullable=True)
    target_file = Column(String, nullable=False)
    change_request = Column(Text, nullable=False)
    sow_markdown = Column(Text, nullable=False)
    search_text = Column(Text, nullable=False)
    replace_text = Column(Text, nullable=False)
    proposed_content = Column(Text, nullable=False)
    screenshot_base64 = Column(Text, nullable=True)
    console_errors_json = Column(Text, default="[]", nullable=False)
    status = Column(String, default="proposed", index=True, nullable=False)
    iteration = Column(Integer, default=1, nullable=False)
    pull_request_url = Column(String, nullable=True)
    pull_request_number = Column(Integer, nullable=True)
    requested_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
