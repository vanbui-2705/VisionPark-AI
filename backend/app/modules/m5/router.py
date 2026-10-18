"""Non-fire M5 reporting and device monitoring APIs."""
import csv
import io
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.users.schemas import RoleName
from app.modules.buildings.models import Building
from app.modules.checkin.models import ParkingTransaction
from app.modules.lanes.models import Lane
from app.modules.m5.models import DailyStat, Device
from app.modules.m5.service import aggregate_day

router = APIRouter(prefix='/m5', tags=['M5 reports and devices'])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[object, Depends(require_roles(RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN))]

def allowed(db, actor, building_id):
    selected = db.info.get('building_id')
    if selected is not None and str(selected) != str(building_id):
        raise AppError(status_code=403, code='BUILDING_SCOPE', message='Building outside selected scope')
    if actor.role.name != RoleName.SYSTEM_ADMIN.value:
        from app.modules.buildings.models import UserBuilding
        membership = db.scalar(select(UserBuilding.id).where(UserBuilding.user_id == actor.id, UserBuilding.building_id == building_id))
        if membership is None:
            raise AppError(status_code=403, code='BUILDING_SCOPE', message='Building outside your scope')

def row_dict(row):
    return {c.name: getattr(row,c.name) for c in row.__table__.columns}

@router.get('/dashboard')
def dashboard(building_id: UUID, db: Db, actor: CurrentUser):
    allowed(db,actor,building_id)
    lane_total = db.scalar(select(func.count()).select_from(Lane).where(Lane.building_id == building_id)) or 0
    lane_active = db.scalar(select(func.count()).select_from(Lane).where(Lane.building_id == building_id, Lane.is_active.is_(True))) or 0
    parked = db.scalar(select(func.count()).select_from(ParkingTransaction).where(ParkingTransaction.building_id == building_id, ParkingTransaction.status == 'PARKED')) or 0
    return {'building_id':building_id,'lanes_total':lane_total,'lanes_active':lane_active,'parked':parked,
            'capacity':None,'available':None,'occupancy_status':'UNKNOWN'}

@router.get('/dashboard/overview')
def overview(db: Db, actor: CurrentUser):
    if actor.role.name != RoleName.SYSTEM_ADMIN.value:
        raise AppError(status_code=403, code='FORBIDDEN', message='System administrator required')
    return [dashboard(b.id, db, actor) for b in db.scalars(select(Building).order_by(Building.name))]

@router.get('/daily-stats')
def stats(building_id: UUID, db: Db, actor: CurrentUser, start: date | None = None, end: date | None = None):
    allowed(db,actor,building_id)
    if start and end and start > end:
        raise AppError(status_code=422, code='INVALID_RANGE', message='start must not exceed end')
    q=select(DailyStat).where(DailyStat.building_id == building_id)
    if start: q=q.where(DailyStat.stat_date >= start)
    if end: q=q.where(DailyStat.stat_date <= end)
    return [row_dict(x) for x in db.scalars(q.order_by(DailyStat.stat_date.desc()).limit(1000))]

@router.get('/daily-stats.csv')
def stats_csv(building_id: UUID, db: Db, actor: CurrentUser, start: date | None = None, end: date | None = None):
    data=stats(building_id,db,actor,start,end)
    f=io.StringIO();w=csv.writer(f)
    keys=['stat_date','vehicle_type','entries','exits','revenue','occupancy_peak']
    w.writerow(keys)
    for r in data: w.writerow([r[k] for k in keys])
    return Response(content='\ufeff'+f.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=m5-report.csv'})

@router.post('/daily-stats/rebuild')
def rebuild(building_id: UUID, day: date, db: Db, actor: Admin):
    allowed(db,actor,building_id)
    result=aggregate_day(db,building_id,day)
    db.commit();db.refresh(result)
    return row_dict(result)

class Heartbeat(BaseModel):
    building_id: UUID
    code: str = Field(min_length=1,max_length=80)
    name: str = Field(min_length=1,max_length=160)
    device_type: str = Field(min_length=1,max_length=40)
    degraded: bool = False

@router.post('/devices/heartbeat')
def heartbeat(payload: Heartbeat, db: Db, actor: Admin):
    allowed(db,actor,payload.building_id)
    device=db.scalar(select(Device).where(Device.building_id == payload.building_id,Device.code == payload.code))
    if device is None:
        device=Device(building_id=payload.building_id,code=payload.code,name=payload.name,device_type=payload.device_type)
        db.add(device)
    device.name=payload.name
    device.status='DEGRADED' if payload.degraded else 'ONLINE'
    device.last_heartbeat_at=datetime.now(timezone.utc)
    db.commit();db.refresh(device)
    return row_dict(device)

@router.get('/devices')
def devices(building_id: UUID, db: Db, actor: CurrentUser, offline_after_seconds: int=Query(90,ge=15,le=86400)):
    allowed(db,actor,building_id)
    now=datetime.now(timezone.utc)
    result=[]
    for device in db.scalars(select(Device).where(Device.building_id == building_id).order_by(Device.code)):
        data=row_dict(device)
        seen=device.last_heartbeat_at
        if seen is None or (now-(seen if seen.tzinfo else seen.replace(tzinfo=timezone.utc))).total_seconds() > offline_after_seconds:
            data['status']='OFFLINE'
        result.append(data)
    return result


@router.get('/daily-stats.pdf')
def stats_pdf(building_id: UUID, db: Db, actor: CurrentUser, start: date | None = None, end: date | None = None):
    """Export the same building-scoped rows as CSV, as a printable PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    rows = stats(building_id, db, actor, start, end)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=32, rightMargin=32)
    style = getSampleStyleSheet()
    content = [Paragraph('VisionPark - M5 Daily Report', style['Title']),
               Paragraph(f'Building: {building_id} | From: {start or "all"} | To: {end or "all"}', style['Normal']), Spacer(1, 16)]
    data = [['Date', 'Vehicle type', 'Entries', 'Exits', 'Revenue (VND)', 'Occupancy peak*']]
    data.extend([[str(x['stat_date']), str(x['vehicle_type']), str(x['entries']), str(x['exits']),
                  str(x['revenue']), str(x['occupancy_peak'])] for x in rows])
    table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=[100, 100, 80, 80, 120, 120])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef7')),
                               ('GRID',(0,0),(-1,-1),0.3,colors.grey),
                               ('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
    content.append(table)
    content.append(Spacer(1, 12))
    content.append(Paragraph('* Occupancy peak is not yet calculated from historical events.', style['Normal']))
    doc.build(content)
    return Response(content=buffer.getvalue(), media_type='application/pdf',
                    headers={'Content-Disposition':'attachment; filename=m5-report.pdf'})

@router.get('/devices/alerts')
def device_alerts(building_id: UUID, db: Db, actor: CurrentUser,
                  offline_after_seconds: int = Query(90, ge=15, le=86400)):
    """Current offline/degraded conditions, derived at request time (not push notifications)."""
    return [x for x in devices(building_id, db, actor, offline_after_seconds)
            if x['status'] in ('OFFLINE', 'DEGRADED')]
