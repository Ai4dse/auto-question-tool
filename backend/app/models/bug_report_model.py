from datetime import datetime, timezone

from mongoengine import DateTimeField, Document, StringField


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BugReport(Document):
    username = StringField(required=True, max_length=128)
    text = StringField(required=True, max_length=4000)
    created_at = DateTimeField(required=True, default=_now_utc)

    meta = {
        "collection": "bug_reports",
        "indexes": ["-created_at", "username"],
    }
