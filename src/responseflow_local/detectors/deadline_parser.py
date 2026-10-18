import re
from datetime import datetime, timedelta

TODAY = re.compile(r"сегодня до (?P<hour>\d{1,2}):(?P<minute>\d{2})", re.I)
TOMORROW = re.compile(r"завтра до (?P<hour>\d{1,2}):(?P<minute>\d{2})", re.I)
HOURS = re.compile(r"в течение (?P<hours>\d+) часов?", re.I)


class InvalidDeadlineError(ValueError):
    pass


def _with_time(base: datetime, hour: int, minute: int) -> datetime:
    try:
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError as error:
        raise InvalidDeadlineError(str(error)) from error


def parse_deadline(text: str, sent_at: datetime) -> datetime | None:
    if match := TODAY.search(text):
        return _with_time(sent_at, int(match["hour"]), int(match["minute"]))

    if match := TOMORROW.search(text):
        tomorrow = sent_at + timedelta(days=1)
        return _with_time(tomorrow, int(match["hour"]), int(match["minute"]))

    if match := HOURS.search(text):
        hours = int(match["hours"])
        if hours <= 0:
            raise InvalidDeadlineError("Количество часов должно быть больше 0.")
        return sent_at + timedelta(hours=hours)

    return None