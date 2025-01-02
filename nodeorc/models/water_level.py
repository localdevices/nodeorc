from datetime import datetime
from pydantic import BaseModel


class WaterLevelTimeSeries(BaseModel):
    timestamp: datetime
    level: float

    def to_db(self):
        from nodeorc import db
        rec = db.models.WaterLevelTimeSeries(
            timestamp=self.timestamp,
            level=self.level
        )
        db.session.add(rec)
        db.session.commit()
