"""Conversation thread model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class ConversationChannel(enum.Enum):
    SMS = "SMS"
    WEB = "WEB"
    PORTAL = "PORTAL"
    PHONE = "PHONE"


class ConversationStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    thread_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(SQLEnum(ConversationChannel, name="conversation_channel"), nullable=False)
    language = Column(String(15), nullable=False)
    started_at = Column(TIMESTAMP, nullable=False)
    ended_at = Column(TIMESTAMP)
    status = Column(SQLEnum(ConversationStatus, name="conversation_status"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
