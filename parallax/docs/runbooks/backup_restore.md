# Backup and Restore Drill

PARALLAX stores authoritative submission state in Postgres and binary/artifact data in MinIO. For local compose environments, run the Postgres drill before release branches and after migration changes:

```bash
python scripts/drill_postgres_restore.py
```

The drill dumps the live compose database, restores it into a disposable database, starts a temporary API pointed at the restored database, and checks that `/api/v1/history` can read prior submissions.

Operational notes:

- Keep managed production backups outside the application cluster.
- Enable PITR/WAL archiving for production Postgres.
- Mirror MinIO buckets (`parallax-apks`, `parallax-quarantine`, `parallax-reports`, `parallax-decompiled`, `parallax-screenshots`) to durable object storage.
- Run `python -m alembic current` after restore and before allowing workers to resume.
- Restore workers only after the API can read submissions and MinIO artifacts are present.
