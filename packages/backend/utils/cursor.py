import base64
import binascii
import json
from datetime import datetime, timezone

from sqlalchemy import and_, or_


def encode_event_cursor(occurred_at: datetime, event_id: int) -> str:
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    value = occurred_at.astimezone(timezone.utc).isoformat()
    payload = json.dumps([value, event_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_event_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        padding = "=" * (-len(cursor) % 4)
        occurred_at_value, event_id = json.loads(
            base64.urlsafe_b64decode(cursor + padding)
        )
        occurred_at = datetime.fromisoformat(occurred_at_value)
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError
        if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id <= 0:
            raise ValueError
        return occurred_at.astimezone(timezone.utc), event_id
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error) as exc:
        raise ValueError("잘못된 이벤트 커서입니다.") from exc


def event_cursor_predicate(model, cursor: str):
    occurred_at, event_id = decode_event_cursor(cursor)
    return or_(
        model.occurred_at < occurred_at,
        and_(model.occurred_at == occurred_at, model.id < event_id),
    )
