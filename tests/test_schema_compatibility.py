"""Additive startup schema repairs for databases predating newer columns."""

from sqlalchemy import create_engine, inspect, text

from elipsis_api.database import ensure_schema_compatibility


def test_missing_login_columns_and_indexes_are_repaired(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, email VARCHAR NOT NULL, "
            "password_hash VARCHAR NOT NULL)"
        ))

    applied = ensure_schema_compatibility(engine)

    assert "users.supabase_id" in applied
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    assert {"supabase_id", "is_admin", "user_type"} <= columns
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    assert "ix_users_supabase_id" in indexes
