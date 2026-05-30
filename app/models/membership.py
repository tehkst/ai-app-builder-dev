from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"), nullable=False)

    role: Mapped[str] = mapped_column(String, default="owner")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
