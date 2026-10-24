import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv

from alembic import context

# Add parent directory to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from backend/.env regardless of CWD
backend_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=backend_env)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set sqlalchemy.url from environment variable
database_url = os.getenv("DATABASE_URL")
if database_url:
    # Alembic uses ConfigParser interpolation, so percent signs must be escaped.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and all models for autogenerate support
from app.database.connection import Base
from app.database.models.organization import Organization
from app.database.models.role import Role
from app.database.models.user import User
from app.database.models.patient_profile import PatientProfile
from app.database.models.staff_profile import StaffProfile
from app.database.models.audit_log import AuditLog
from app.database.models.patient_consent_record import PatientConsentRecord
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.care_navigation_episode import CareNavigationEpisode
from app.database.models.conversation_thread import ConversationThread
from app.database.models.conversation_message import ConversationMessage
from app.database.models.clinical_guardrail import ClinicalGuardrail
from app.database.models.clinical_guardrail_rule import ClinicalGuardrailRule
from app.database.models.conversation_guardrail_hit import ConversationGuardrailHit
from app.database.models.emergency_event import EmergencyEvent
from app.database.models.care_team_queue import CareTeamQueue
from app.database.models.queue_membership import QueueMembership
from app.database.models.escalation import Escalation
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.escalation_action import EscalationAction
from app.database.models.outreach_campaign import OutreachCampaign
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.outreach_event import OutreachEvent
from app.database.models.staff_availability import StaffAvailability
from app.database.models.appointment import Appointment
from app.database.models.checkin_template import CheckinTemplate
from app.database.models.checkin_template_review import CheckinTemplateReview
from app.database.models.checkin_question import CheckinQuestion
from app.database.models.notification import Notification

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
