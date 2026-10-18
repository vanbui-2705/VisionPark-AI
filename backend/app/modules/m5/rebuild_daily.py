"""Run once daily using Windows Task Scheduler or cron, after local midnight."""
import argparse
from datetime import date, timedelta
from sqlalchemy import select
from app.database.session import database
from app.core.config import get_settings
from app.modules.buildings.models import Building
from app.modules.m5.service import aggregate_day

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--day',type=date.fromisoformat,default=date.today()-timedelta(days=1))
    args=parser.parse_args()
    database.configure(get_settings().database_url)
    with database.create_session() as db:
        for building in db.scalars(select(Building)).all():
            aggregate_day(db,building.id,args.day)
        db.commit()
if __name__ == '__main__': main()
