"""Conversation message model."""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey, TIMESTAMP, Integer, Index, JSON
from app.database.connection import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    message_id = Column(BigInteger, primary_key=True, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False, index=True)
    sender_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    ai_model_name = Column(String(80))
    ai_model_version = Column(String(40))
    message_text = Column(Text, nullable=False)
    message_intent = Column(String(80), index=True)
    readability_grade = Column(Integer)
    is_guardrail_override = Column(Boolean, nullable=False, server_default="false")
    message_metadata = Column(JSON)
    sent_at = Column(TIMESTAMP, nullable=False, index=True)


Index("ix_conversation_messages_thread_sent", ConversationMessage.thread_id, ConversationMessage.sent_at)
