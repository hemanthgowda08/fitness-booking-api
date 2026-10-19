"""Small, repeatable SQLite migrations for installations created before new columns."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _column_names(engine: Engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def migrate_database(engine: Engine) -> None:
    """Add role and cancellation columns without dropping existing SQLite data."""
    tables = set(inspect(engine).get_table_names())
    if "users" in tables:
        user_columns = _column_names(engine, "users")
        if "role" not in user_columns:
            # SQLite applies this non-null default to every existing user.
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'member'"))

    if "fitness_classes" in tables:
        class_columns = _column_names(engine, "fitness_classes")
        additions = (
            ("creator_id", "ALTER TABLE fitness_classes ADD COLUMN creator_id INTEGER"),
            ("is_cancelled", "ALTER TABLE fitness_classes ADD COLUMN is_cancelled BOOLEAN NOT NULL DEFAULT 0"),
            ("cancelled_at", "ALTER TABLE fitness_classes ADD COLUMN cancelled_at DATETIME"),
        )
        with engine.begin() as connection:
            for column, statement in additions:
                if column not in class_columns:
                    connection.execute(text(statement))
