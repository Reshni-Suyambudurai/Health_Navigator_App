"""Triggering response links for a session-level check-in escalation."""

from sqlalchemy import BigInteger, Column, ForeignKey

from app.database.connection import Base


class CheckinEscalationResponse(Base):
    __tablename__ = "checkin_escalation_responses"

    checkin_escalation_id = Column(
        BigInteger,
        ForeignKey("checkin_escalations.checkin_escalation_id", ondelete="CASCADE"),
        primary_key=True,
    )
    response_id = Column(
        BigInteger,
        ForeignKey("checkin_responses.response_id", ondelete="CASCADE"),
        primary_key=True,
    )