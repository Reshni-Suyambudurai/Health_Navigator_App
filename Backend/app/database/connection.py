"""
Database connection management for Patient AI Health Navigator
Handles SQLAlchemy engine creation and session management
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.config import settings
from app.core.exceptions import PatientFHIRException
import logging

logger = logging.getLogger(__name__)

# Create SQLAlchemy Base for ORM models
Base = declarative_base()

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Create Monster DB engine for PatientFHIR read operations
monster_engine = None
if settings.resolved_monster_database_url:
    monster_engine = create_engine(
        settings.resolved_monster_database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

MonsterSessionLocal = None
if monster_engine is not None:
    MonsterSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=monster_engine
    )


def get_db():
    """
    Dependency function to get database session
    Usage in FastAPI endpoints:
        def endpoint(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_monster_db():
    """
    Dependency function to get Monster database session.
    Used only for read access to patient FHIR records.
    """
    if MonsterSessionLocal is None:
        raise PatientFHIRException(
            "Monster database is not configured. Set MONSTER_DATABASE_URL "
            "or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD in .env",
            error_code="PATIENT_FHIR_002"
        )

    db = MonsterSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_monster_db():
    """Yield a read-only Monster session when configured, otherwise None."""
    if MonsterSessionLocal is None:
        yield None
        return

    db = MonsterSessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Check if database connection is working
    Returns True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


def check_monster_database_connection() -> bool:
    """
    Check if Monster database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    if monster_engine is None:
        logger.warning("Monster database not configured")
        return False

    try:
        with monster_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Monster database connection successful")
        return True
    except Exception as e:
        logger.error(f"Monster database connection failed: {str(e)}")
        return False


def init_db():
    """
    Initialize database by creating all tables
    Note: This is primarily for ORM models, not SQL migrations
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}")
        raise
