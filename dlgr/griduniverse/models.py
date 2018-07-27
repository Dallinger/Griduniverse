from dallinger.models import Info
from dallinger.information import State
from sqlalchemy import Column, Index
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


if 'state_walls_idx' not in (index.name for index in State.__table__.indexes):
    # If the index is already defined then this module is being loaded for a second time.
    # Do not declare the index in that case, or SQLAlchemy will see it as a duplicate
    state_walls_index = Index('state_walls_idx', State.details['walls'], postgresql_using='gin')
    state_food_index = Index('state_food_idx', State.details['food'], postgresql_using='gin')
    info_type_index = Index('info_type_idx', Info.details['type'].astext)
