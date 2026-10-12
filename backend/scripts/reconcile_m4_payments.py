"""Run a single building's mock payment reconciliation in the foreground."""

import argparse
import json
from uuid import UUID

from app.core.config import get_settings
from app.database.session import database
from app.modules.pricing.billing import reconcile_payments


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--building-id", type=UUID, required=True)
    building_id = parser.parse_args().building_id
    database.configure(get_settings().database_url)
    try:
        with database.create_session() as session:
            mismatches = reconcile_payments(session, building_id=building_id)
        print(json.dumps({"building_id": str(building_id), "mismatches": mismatches}))
        return 1 if mismatches else 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
