from dallinger.models import Info
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declared_attr


class Event(Info):
    """An event."""

    __mapper_args__ = {
        "polymorphic_identity": "event"
    }

    def __init__(self, origin, details):
        super(Event, self).__init__(origin)
        self.details = details

    @declared_attr
    def details(cls):
        "details column, if not present already."
        return Info.__table__.c.get('details', Column(JSONB))