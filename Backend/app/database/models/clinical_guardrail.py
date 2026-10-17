"""Clinical guardrail model."""

from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class ClinicalGuardrail(Base):
    __tablename__ = "clinical_guardrail"

    guardrail_id = Column(BigInteger, primary_key=True, index=True)
    guardrail_name = Column(String(255), nullable=False, unique=True)
    guardrail_markdown = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
