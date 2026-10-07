"""Compare operational records projected onto the original columns across an additive upgrade."""

import argparse
import hashlib
import json
from pathlib import Path

from data_backup import inventory, run


def sql(query):
    return run(
        "exec",
        "visionpark-db-1",
        "sh",
        "-c",
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"',
        "sh",
        query,
    )


def snapshot(columns):
    result = {}
    for table, names in columns.items():
        projection = ",".join('"' + name + '"' for name in names)
        rows = sql(
            f'SELECT row_to_json(t)::text FROM (SELECT {projection} FROM "{table}") t '
            "ORDER BY row_to_json(t)::text"
        )
        result[table] = {
            "count": len(rows.splitlines()),
            "sha256": hashlib.sha256(rows).hexdigest(),
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["baseline", "check"])
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "baseline":
        if args.file.exists():
            raise ValueError("Baseline destination already exists")
        columns = {}
        for line in (
            sql(
                "SELECT table_name,column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name!='alembic_version' "
                "ORDER BY table_name,ordinal_position"
            )
            .decode()
            .splitlines()
        ):
            table, column = line.split("|")
            columns.setdefault(table, []).append(column)
        data = {
            "columns": columns,
            "tables": snapshot(columns),
            "storage": inventory("visionpark-db-1", "visionpark-backend-1"),
        }
        args.file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        data = json.loads(args.file.read_text(encoding="utf-8"))
        assert snapshot(data["columns"]) == data["tables"], "Original records changed"
        current = inventory("visionpark-db-1", "visionpark-backend-1")
        assert current["volumes"] == data["storage"]["volumes"], "Volume names changed"
        assert current["media"] == data["storage"]["media"], "Media hashes changed"
        print(
            json.dumps(
                {
                    "original_tables_preserved": len(data["tables"]),
                    "images_preserved": len(current["media"]),
                    "volumes": current["volumes"],
                }
            )
        )


if __name__ == "__main__":
    main()
