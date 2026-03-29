"""
Migration script to add system_reminders table for deduplication.

Run: python scripts/migrate_system_reminders.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import DATABASE_PATH

Base = declarative_base()


class SystemReminder(Base):
    """Deduplicated system-reminder content."""
    __tablename__ = 'system_reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    content = Column(String, nullable=False)
    first_seen_at = Column(DateTime, nullable=False)
    use_count = Column(Integer, default=1)

    __table_args__ = (
        Index('idx_system_reminders_hash', 'content_hash'),
    )


def migrate():
    """Create system_reminders table."""
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)

    # Check if table exists
    from sqlalchemy import inspect
    inspector = inspect(engine)

    if 'system_reminders' in inspector.get_table_names():
        print("system_reminders table already exists, skipping.")
        return

    # Create table
    Base.metadata.create_all(engine, tables=[SystemReminder.__table__])
    print("✓ Created system_reminders table")

    # Show stats
    Session = sessionmaker(bind=engine)
    session = Session()
    count = session.query(SystemReminder).count()
    print(f"  Table ready. Current records: {count}")
    session.close()


if __name__ == "__main__":
    migrate()
    print("\nMigration complete!")
    print("New requests will automatically deduplicate system-reminder content.")
