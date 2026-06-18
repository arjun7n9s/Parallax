# Operational Runbooks

## Local Development Setup

1. Start infrastructure: `docker compose up -d`
2. Initialize Neo4j graph: `python scripts/init_neo4j.py`
3. Apply DB migrations: `alembic upgrade head`
4. Start API: `uvicorn parallax.api.main:app --reload`

## Troubleshooting

## Backup and Restore

Run the local compose drill with:

```bash
python scripts/drill_postgres_restore.py
```

See [backup_restore.md](backup_restore.md) for the full procedure and production notes.

### Neo4j won't start
- Check logs: `docker logs parallax_neo4j`
- Verify password matches `.env`: `NEO4J_PASSWORD`

### Ollama out of memory
- Reduce model size: use `phi3:mini` instead of larger models
- Check GPU memory: `nvidia-smi`

### MinIO health check failing
- Ensure port 9000 is not occupied by another service
- Check MinIO console at `http://localhost:9001`
