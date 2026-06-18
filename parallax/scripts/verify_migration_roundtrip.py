"""Smoke-test the latest migration on a seeded disposable database.

This intentionally refuses to run when application tables already exist. Point
POSTGRES_DB at a throwaway database before running locally.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parallax.core.config import settings

BASE_TABLES = {"submissions", "iocs", "audit_log"}
SEED_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_IOC_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
SEED_AUDIT_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
TENANT_B_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
SEED_SHA = "a" * 64


def _run_alembic(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "alembic", *args], check=True)


def _engine() -> sa.Engine:
    return sa.create_engine(settings.POSTGRES_URL_SYNC, future=True)


def _application_tables(conn: sa.Connection) -> set[str]:
    rows = conn.execute(
        sa.text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename != 'alembic_version'
            """
        )
    )
    return {str(row[0]) for row in rows}


def _assert_disposable_database() -> None:
    with _engine().connect() as conn:
        tables = _application_tables(conn)
    if tables:
        raise RuntimeError(
            "Migration roundtrip smoke test requires an empty disposable database; "
            f"found existing tables: {sorted(tables)}"
        )


def _seed_pre_tenant_schema() -> None:
    with _engine().begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO submissions
                    (id, sha256, md5, file_name, file_size, status, priority, s3_path)
                VALUES
                    (:id, :sha256, :md5, :file_name, :file_size, 'complete', 'normal', :s3_path)
                """
            ),
            {
                "id": SEED_ID,
                "sha256": SEED_SHA,
                "md5": "b" * 32,
                "file_name": "seed.apk",
                "file_size": 1234,
                "s3_path": f"s3://parallax-apks/{SEED_SHA}.apk",
            },
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO iocs (id, submission_id, ioc_type, value, confidence)
                VALUES (:id, :submission_id, 'domain', 'seed.example', 0.8)
                """
            ),
            {"id": SEED_IOC_ID, "submission_id": SEED_ID},
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO audit_log (id, submission_id, actor, action, detail)
                VALUES (:id, :submission_id, 'migration-smoke', 'seed.created', '{"ok": true}')
                """
            ),
            {"id": SEED_AUDIT_ID, "submission_id": SEED_ID},
        )


def _one(conn: sa.Connection, sql: str, **params: object) -> object:
    return conn.execute(sa.text(sql), params).scalar_one()


def _assert_upgraded() -> None:
    with _engine().begin() as conn:
        for table in BASE_TABLES:
            columns = {
                str(row[0])
                for row in conn.execute(
                    sa.text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        """
                    ),
                    {"table_name": table},
                )
            }
            assert "tenant_id" in columns, f"{table}.tenant_id missing after upgrade"

        tenant = _one(conn, "SELECT tenant_id FROM submissions WHERE id = :id", id=SEED_ID)
        assert tenant == "default", f"seed tenant backfill failed: {tenant!r}"

        conn.execute(
            sa.text(
                """
                INSERT INTO submissions
                    (id, tenant_id, sha256, md5, file_name, file_size, status, priority, s3_path)
                VALUES
                    (:id, 'tenant-b', :sha256, :md5, 'same-hash.apk', 1234,
                     'complete', 'normal', :s3_path)
                """
            ),
            {
                "id": TENANT_B_ID,
                "sha256": SEED_SHA,
                "md5": "c" * 32,
                "s3_path": f"s3://parallax-apks/{SEED_SHA}-tenant-b.apk",
            },
        )
        duplicate_count = _one(
            conn, "SELECT count(*) FROM submissions WHERE sha256 = :sha256", sha256=SEED_SHA
        )
        assert duplicate_count == 2, (
            "tenant-scoped SHA uniqueness did not allow cross-tenant duplicate"
        )
        conn.execute(sa.text("DELETE FROM submissions WHERE id = :id"), {"id": TENANT_B_ID})


def _assert_downgraded_without_data_loss() -> None:
    with _engine().connect() as conn:
        columns = {
            str(row[0])
            for row in conn.execute(
                sa.text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'submissions'
                    """
                )
            )
        }
        assert "tenant_id" not in columns, "tenant_id survived downgrade to 0008"
        count = _one(conn, "SELECT count(*) FROM submissions WHERE id = :id", id=SEED_ID)
        assert count == 1, "seed submission was lost during upgrade/downgrade"
        ioc_count = _one(conn, "SELECT count(*) FROM iocs WHERE id = :id", id=SEED_IOC_ID)
        audit_count = _one(conn, "SELECT count(*) FROM audit_log WHERE id = :id", id=SEED_AUDIT_ID)
        assert ioc_count == 1, "seed IOC was lost during upgrade/downgrade"
        assert audit_count == 1, "seed audit row was lost during upgrade/downgrade"


def main() -> None:
    if settings.POSTGRES_DB in {"parallax", "postgres"} and not os.getenv(
        "ALLOW_DEFAULT_DB_MIGRATION_SMOKE"
    ):
        raise RuntimeError(
            "Refusing to run migration roundtrip against the default database. "
            "Set POSTGRES_DB to a disposable database."
        )

    _assert_disposable_database()
    _run_alembic("upgrade", "0008_add_batch_id")
    _seed_pre_tenant_schema()
    _run_alembic("upgrade", "head")
    _assert_upgraded()
    _run_alembic("downgrade", "0008_add_batch_id")
    _assert_downgraded_without_data_loss()
    _run_alembic("upgrade", "head")
    print("Migration roundtrip smoke test passed")


if __name__ == "__main__":
    main()
