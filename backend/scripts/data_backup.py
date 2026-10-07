"""Consistent Docker database/media backup and isolated restore. Never deletes volumes."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def run(*args: str) -> bytes:
    return subprocess.check_output(["docker", *args])


def inventory(db: str, backend: str, media_folder: Path | None = None) -> dict:
    objects = json.loads(run("inspect", db, backend))
    volumes = {m["Name"] for o in objects for m in o["Mounts"] if m["Type"] == "volume"}
    query = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    tables = (
        run(
            "exec",
            db,
            "sh",
            "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"',
            "sh",
            query,
        )
        .decode()
        .splitlines()
    )
    data = {}
    for table in tables:
        sql = f'SELECT row_to_json(t)::text FROM "{table}" t ORDER BY row_to_json(t)::text'
        rows = run(
            "exec",
            db,
            "sh",
            "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"',
            "sh",
            sql,
        )
        data[table] = {"count": len(rows.splitlines()), "sha256": hashlib.sha256(rows).hexdigest()}
    media = (
        {
            str(p.relative_to(media_folder)).replace("\\", "/"): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in media_folder.rglob("*")
            if p.is_file()
        }
        if media_folder
        else json.loads(
            run(
                "exec",
                backend,
                "python",
                "-c",
                "import pathlib,hashlib,json; p=pathlib.Path('/app/var/media'); "
                "print(json.dumps({str(f.relative_to(p)):"
                "hashlib.sha256(f.read_bytes()).hexdigest() "
                "for f in p.rglob('*') if f.is_file()}))",
            )
        )
    )
    return {"volumes": sorted(volumes), "tables": data, "media": media}


def backup(folder: Path, db: str, backend: str) -> None:
    folder.mkdir(parents=True, exist_ok=False)
    run("pause", backend)
    try:
        dump = run("exec", db, "sh", "-c", 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc')
        (folder / "database.dump").write_bytes(dump)
        run("cp", f"{backend}:/app/var/media", str(folder / "media"))
        baseline = inventory(db, backend, folder / "media")
    finally:
        run("unpause", backend)
    baseline["created_at"] = datetime.now(UTC).isoformat()
    baseline["database_sha256"] = hashlib.sha256(dump).hexdigest()
    (folder / "manifest.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "backup": str(folder),
                "tables": baseline["tables"],
                "media_files": len(baseline["media"]),
            }
        )
    )


def restore(folder: Path, target: str) -> None:
    if not target.startswith("visionpark-restore-"):
        raise ValueError("Restore target must start with visionpark-restore- and be isolated")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    dump = (folder / "database.dump").read_bytes()
    if hashlib.sha256(dump).hexdigest() != manifest["database_sha256"]:
        raise ValueError("Backup checksum mismatch")
    inspect = json.loads(run("inspect", target))[0]
    if any(m.get("Name") in manifest["volumes"] for m in inspect["Mounts"]):
        raise ValueError("Restore target mounts an operational volume")
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            target,
            "sh",
            "-c",
            'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --exit-on-error',
        ],
        input=dump,
        check=True,
    )
    run("cp", str(folder / "media"), f"{target}:/restore-media")
    for table, expected in manifest["tables"].items():
        sql = f'SELECT row_to_json(t)::text FROM "{table}" t ORDER BY row_to_json(t)::text'
        rows = run(
            "exec",
            target,
            "sh",
            "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"',
            "sh",
            sql,
        )
        if hashlib.sha256(rows).hexdigest() != expected["sha256"]:
            raise ValueError(f"Restored table mismatch: {table}")
    for key, expected in manifest["media"].items():
        if hashlib.sha256((folder / "media" / key).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Media mismatch: {key}")
        restored_hash = (
            run("exec", target, "sha256sum", f"/restore-media/{key}").decode().split()[0]
        )
        if restored_hash != expected:
            raise ValueError(f"Restored media mismatch: {key}")
    print(
        json.dumps(
            {
                "restore": target,
                "verified_tables": len(manifest["tables"]),
                "verified_media": len(manifest["media"]),
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore", "inventory"])
    parser.add_argument("--folder", type=Path)
    parser.add_argument("--db", default="visionpark-db-1")
    parser.add_argument("--backend", default="visionpark-backend-1")
    parser.add_argument("--target")
    args = parser.parse_args()
    if args.action == "inventory":
        print(json.dumps(inventory(args.db, args.backend), indent=2))
    elif args.action == "backup":
        backup(args.folder.resolve(), args.db, args.backend)
    else:
        restore(args.folder.resolve(), args.target)


if __name__ == "__main__":
    main()
