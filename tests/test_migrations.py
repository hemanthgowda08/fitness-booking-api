from sqlalchemy import create_engine, inspect, text

from migrations import migrate_database


def test_legacy_records_survive_repeatable_role_and_cancellation_migration(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100), email VARCHAR(255), password_hash VARCHAR(255), created_at DATETIME)"))
        connection.execute(text("CREATE TABLE fitness_classes (id INTEGER PRIMARY KEY, name VARCHAR(100), instructor VARCHAR(100), date_time DATETIME, total_slots INTEGER, available_slots INTEGER)"))
        connection.execute(text("CREATE TABLE bookings (id INTEGER PRIMARY KEY, user_id INTEGER, class_id INTEGER, booked_at DATETIME)"))
        connection.execute(text("INSERT INTO users VALUES (1, 'Legacy', 'legacy@example.com', 'hash', '2030-01-01 00:00:00')"))
        connection.execute(text("INSERT INTO fitness_classes VALUES (1, 'Yoga', 'Maya', '2030-01-02 10:00:00', 4, 3)"))
        connection.execute(text("INSERT INTO bookings VALUES (1, 1, 1, '2030-01-01 00:00:00')"))
    migrate_database(engine)
    migrate_database(engine)
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    class_columns = {column["name"] for column in inspect(engine).get_columns("fitness_classes")}
    assert "role" in user_columns
    assert {"creator_id", "is_cancelled", "cancelled_at"}.issubset(class_columns)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT role FROM users WHERE id = 1")).scalar_one() == "member"
        assert connection.execute(text("SELECT creator_id, is_cancelled FROM fitness_classes WHERE id = 1")).one() == (None, 0)
        assert connection.execute(text("SELECT COUNT(*) FROM bookings")).scalar_one() == 1
