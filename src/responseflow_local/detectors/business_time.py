from datetime import datetime, time, timedelta

WORK_START = time(9, 0)
WORK_END = time(18, 0)


def _get_tz(dt: datetime):
    return dt.tzinfo


def is_working_day(value: datetime) -> bool:
    return value.isoweekday() in {1, 2, 3, 4, 5}


def _next_working_start(dt: datetime) -> datetime:
    tz = _get_tz(dt)

    if dt.time() >= WORK_END or not is_working_day(dt):
        dt = datetime.combine(dt.date() + timedelta(days=1), time.min, tzinfo=tz)
        while not is_working_day(dt):
            dt = datetime.combine(dt.date() + timedelta(days=1), time.min, tzinfo=tz)
        return datetime.combine(dt.date(), WORK_START, tzinfo=tz)

    if dt.time() < WORK_START:
        return datetime.combine(dt.date(), WORK_START, tzinfo=tz)

    return dt


def add_working_minutes(start: datetime, minutes: int) -> datetime:

    if minutes <= 0:
        return _next_working_start(start)

    current = _next_working_start(start)

    remaining = minutes
    tz = _get_tz(current)

    while remaining > 0:

        day_end = datetime.combine(current.date(), WORK_END, tzinfo=tz)
        until_end = int((day_end - current).total_seconds() // 60)

        if remaining <= until_end:
            result = current + timedelta(minutes=remaining)
            return result

        remaining -= until_end
        current = datetime.combine(
            current.date() + timedelta(days=1),
            WORK_START,
            tzinfo=tz,
        )

        while not is_working_day(current):
            current = datetime.combine(
                current.date() + timedelta(days=1),
                WORK_START,
                tzinfo=tz,
            )

    return current


def working_minutes_between(start: datetime, end: datetime) -> int:
    if start >= end:
        return 0

    start_norm = _next_working_start(start)
    tz = _get_tz(start_norm)

    if tz is not None and end.tzinfo is not None:
        end_norm = end.astimezone(tz)
    else:
        end_norm = end

    if start_norm >= end_norm:
        return 0

    total_minutes = 0
    current_date = start_norm.date()

    while current_date <= end_norm.date():
        day_start = datetime.combine(
            current_date, WORK_START, tzinfo=tz
        )
        day_end = datetime.combine(
            current_date, WORK_END, tzinfo=tz
        )

        if is_working_day(day_start):
            interval_start = max(start_norm, day_start)
            interval_end = min(end_norm, day_end)

            if interval_start < interval_end:
                total_minutes += int(
                    (interval_end - interval_start).total_seconds()
                    // 60
                )

        if current_date == end_norm.date():
            break

        current_date += timedelta(days=1)

    return total_minutes
