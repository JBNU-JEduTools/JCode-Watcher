from crud.event import insert_event_once
from models.buildLog import BuildLog
from models.runLog import RunLog
from sqlmodel import Session


def build_register(db: Session, build_data):
    return insert_event_once(db, BuildLog, build_data)


def run_register(db: Session, run_data):
    return insert_event_once(db, RunLog, run_data)
