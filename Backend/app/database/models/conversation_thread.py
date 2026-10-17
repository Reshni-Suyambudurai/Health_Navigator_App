"""Conversation thread model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    thread_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(30), nullable=False)
    language = Column(String(15), nullable=False)
    started_at = Column(TIMESTAMP, nullable=False)
    ended_at = Column(TIMESTAMP)
    status = Column(String(30), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
