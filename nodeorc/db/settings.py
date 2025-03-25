"""Model for settings."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean
from sqlalchemy.orm import validates
from nodeorc.db import Base


class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    parse_dates_from_file = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag determining if dates should be read from a datestring in the filename (True, default) or from "
                "the file metadata (False)"
    )
    video_file_fmt = Column(
        String,
        nullable=False,
        comment="Filename template (excluding path) defining the file name convention of video files. The template "
                "contains a datestring format in between {} signs, e.g. video_{%Y%m%dT%H%M%S}.mp4"
    )
    allowed_dt = Column(
        Float,
        default=3600,
        nullable=False,
        comment="Float indicating the maximum difference in time allowed between a videofile time stamp and a water "
                "level time stamp to match them"
    )
    shutdown_after_task = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag for enabling automated shutdown after a task is performed. Must only be used if a power cycling "
                "scheme is implemented and is meant to save power only."
    )
    reboot_after = Column(
        Float,
        default=0,
        nullable=False,
        comment="Float indicating the amount of seconds after which device reboots (0 means never reboot)"
    )
    enable_daemon = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag for enabling the daemon. If disabled, the daemon will not be started and the service will "
                "only run in the foreground."
    )
    def __str__(self):
        return "Settings {} ({})".format(self.created_at, self.id)

    def __repr__(self):
        return "{}".format(self.__str__())

    @validates("video_file_fmt")
    def check_video_fmt(cls, key, value):
        if value.replace(" ", "") == "":
            raise ValueError("video_file_fmt cannot be empty")
        # check string within {}, see if that can be parsed to datetime
        check_datetime_fmt(cls, value)
        return value


def check_datetime_fmt(cls, fn_fmt):
    # check string within {}, see if that can be parsed to datetime
    if not("{" in fn_fmt and "}" in fn_fmt):
        # there is no datestring in format, then cls.parse_dates_from_file MUST be False
        if cls.parse_dates_from_file:
            raise ValueError(
                '{:s} does not contain a datetime format between {{""}} signs. Either set parse_dates_from_file to False '
                'or provide a filename template with datetime format between {{""}}'.format(fn_fmt)
            )
        return True
    try:
        fmt = fn_fmt.split('{')[1].split('}')[0]
    except:
        raise ValueError('{:s} does not contain a datetime format between {""} signs'.format(fn_fmt))
    datestr = datetime(2000, 1, 1, 1, 1, 1).strftime(fmt)
    dt = datetime.strptime(datestr, fmt)
    if dt.year != 2000 or dt.month != 1 or dt.day != 1:
        raise ValueError(f'Date format "{fmt}" is not a valid date format pattern')
    return True

