"""Rotation engine: pure functions answering "whose turn is it?".

Implements the plan's formula

    assignee_index = (periods_elapsed(chore.period) + chore.offset) % len(people)

under the settled date rules (_docs/decision-week-boundary-timezone.md):
weeks start on the configured week_start day (only Monday is valid for
now), all date arithmetic runs in the configured timezone, and period
index 0 is the period containing the anchor date. Dates before the anchor
produce negative period indices, and the true mathematical modulo in
assignee_index extrapolates the rotation backwards cleanly.

Stdlib only — no Django, no I/O, no config-file knowledge. Callers pass the
validated config values in; the schedule stays a pure function of the date
and those values.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

VALID_PERIODS = ("daily", "weekly", "monthly")

# ISO weekday numbers for the values week_start may take. Only Monday is
# valid for now (decision doc), but the engine reads it from the caller
# rather than hardcoding it.
_WEEK_START_WEEKDAYS = {"monday": 0}


def local_date(at, timezone):
    """The calendar date of instant `at` on the household's clock.

    `at` must be an aware datetime. There is exactly one rotation clock —
    `timezone`, not the viewer's — so every "whose turn is it now" question
    starts by converting the instant to a date here.
    """
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError(f"at must be an aware datetime, got {at!r}")
    return at.astimezone(ZoneInfo(timezone)).date()


def periods_elapsed(period, on, *, anchor, week_start="monday"):
    """Whole `period`s between the period containing `anchor` and the period
    containing date `on`.

    Negative when `on` falls in an earlier period than the anchor. The
    anchor is a plain date naming which period is period zero; datetimes
    must be reduced to dates via local_date() first.
    """
    if period == "daily":
        return (on - anchor).days
    if period == "weekly":
        start = _week_start_weekday(week_start)
        anchor_week = anchor - timedelta(days=(anchor.weekday() - start) % 7)
        on_week = on - timedelta(days=(on.weekday() - start) % 7)
        return (on_week - anchor_week).days // 7
    if period == "monthly":
        return (on.year - anchor.year) * 12 + (on.month - anchor.month)
    raise ValueError(
        f"unknown period {period!r}; expected one of {', '.join(VALID_PERIODS)}"
    )


def period_bounds(period, on, *, timezone, week_start="monday"):
    """(start, end) of the period containing date `on`, as aware datetimes:
    midnight local in `timezone`, start inclusive, end exclusive.

    Bounds are civil (wall-clock) midnights, so around a DST change a bound
    never falls at 01:00 or 23:00 — a week spanning a clock change simply
    contains a 23- or 25-hour day.
    """
    tz = ZoneInfo(timezone)
    if period == "daily":
        start_date = on
        end_date = on + timedelta(days=1)
    elif period == "weekly":
        start = _week_start_weekday(week_start)
        start_date = on - timedelta(days=(on.weekday() - start) % 7)
        end_date = start_date + timedelta(days=7)
    elif period == "monthly":
        start_date = on.replace(day=1)
        end_date = date(
            start_date.year + start_date.month // 12, start_date.month % 12 + 1, 1
        )
    else:
        raise ValueError(
            f"unknown period {period!r}; expected one of {', '.join(VALID_PERIODS)}"
        )
    midnight = time(0, 0)
    return (
        datetime.combine(start_date, midnight, tz),
        datetime.combine(end_date, midnight, tz),
    )


def assignee_index(period, offset, num_people, on, *, anchor, week_start="monday"):
    """The plan's formula: (periods_elapsed(period) + chore.offset) % len(people).

    Python's % is a true mathematical modulo, so negative period indices
    (dates before the anchor) still land in 0 .. num_people-1.
    """
    if num_people < 1:
        raise ValueError(f"num_people must be at least 1, got {num_people}")
    elapsed = periods_elapsed(period, on, anchor=anchor, week_start=week_start)
    return (elapsed + offset) % num_people


def _week_start_weekday(week_start):
    try:
        return _WEEK_START_WEEKDAYS[week_start]
    except KeyError:
        raise ValueError(
            f'unsupported week_start {week_start!r}; only "monday" is valid for now'
        ) from None
