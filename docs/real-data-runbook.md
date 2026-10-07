# Real data operations

Operational volumes: `visionpark_postgres_data`, `visionpark_media_data`.
Application seed is disabled by default. It never resets existing accounts or inserts example detections/transactions.

## Consistent backup

Pause application writes while taking the database/media pair. The script temporarily pauses the backend, copies media, produces a PostgreSQL custom-format dump and a manifest, and unpauses the backend in `finally`.
Keep the backup outside application volumes. The destination must be new.

```powershell
py -3 backend/scripts/data_backup.py backup --folder E:\BE_AI\VisionPark-backups\YOUR-NEW-BACKUP
```

Manifest includes table row counts/hashes, media SHA256 and original volume names. Credentials are not included. Limit other database writers during the backup window.

## Isolated restore

Use a NEW PostgreSQL container/database named `visionpark-restore-*`. It must not mount operational volumes. Restore refuses operational volume mounts and uses `pg_restore --exit-on-error` without clearing a target.

```powershell
docker compose -f deployment/compose.persistence-test.yml up -d db
# Wait for database health before restoring into this empty test database.
py -3 backend/scripts/data_backup.py restore --folder E:\BE_AI\VisionPark-backups\YOUR-BACKUP --target visionpark-restore-e2e-db
```

The restore verifies database row hashes and copies/verifies media under `/restore-media` in the isolated container. To run an application against it, copy this media into the isolated backend's `/app/var/media` before serving requests. Do not connect a restored application to operational volumes.

## Upgrade and lifecycle

After verifying restore and migration compatibility:

```powershell
docker compose up --build -d
docker compose ps
docker compose exec -T backend alembic current
```

`restart`, `up --build` and `up --force-recreate` retain the named database/media volumes. `down` retains them unless `-v` is supplied. Never use `down -v`, prune volumes or delete media when preserving data.
Check volume names, migration head, existing row IDs/counts and image hashes before and after an upgrade.

## Compatible rollback

Keep added tables/columns and roll back application code only when that version can read the current schema. Migration 0009 refuses downgrade when persistent workflow data exists. Restore a verified backup into a separate database if a full rollback is needed; review and switch connections deliberately rather than dropping live schema.

## Storage inspection

```powershell
docker compose exec -T backend python -c "from pathlib import Path; print(sum(p.stat().st_size for p in Path('/app/var/media').rglob('*') if p.is_file()))"
cd backend
py -3 scripts/audit_media.py
```

The audit is read-only. Missing files and orphan files need investigation; there is no automatic deletion/retention job. Monitor database/media volume capacity separately from readiness.

## Current backup evidence

`E:\BE_AI\VisionPark-backups\20261007-verified` was restored into an isolated database and all 7 table hashes and 4 image hashes matched. Migration 0009 was tested on a restored database; see `phase-2-evidence/completion-migration-preservation.json`.
Old records without source evidence remain unknown; backups do not relabel or delete them.

The final application schema is `20261007_0010`. The post-upgrade backup
`E:\BE_AI\VisionPark-backups\20261007-after-real-completion` was independently restored
into `visionpark-restore-postupgrade`: all 10 table hashes and 4 image hashes matched.
The original six business tables and four images still match the pre-upgrade baseline.

For a new installation only, bootstrap requires an explicitly supplied admin password
of at least eight characters. Existing deployments keep `AUTO_SEED=false`.
