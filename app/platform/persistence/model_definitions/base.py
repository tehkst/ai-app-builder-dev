from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base


PlatformBase = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)
