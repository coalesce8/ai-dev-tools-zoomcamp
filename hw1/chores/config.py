"""Load and validate the household config file.

People and chores come from a version-controlled YAML file, never the
database (see _docs/plan.md). The file is validated once at startup via
ChoresConfig.ready(); anything wrong raises ImproperlyConfigured so the app
fails loudly instead of serving a broken schedule.
"""

from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

VALID_PERIODS = ("daily", "weekly", "monthly")
VALID_WEEK_STARTS = ("monday",)  # decision doc: only Monday is valid for now

_TOP_LEVEL_KEYS = {
    "week_start",
    "timezone",
    "anchor_date",
    "url_token",
    "people",
    "chores",
}
_CHORE_KEYS = {"name", "period", "offset"}


@dataclass(frozen=True)
class Chore:
    name: str
    period: str  # one of VALID_PERIODS
    offset: int


@dataclass(frozen=True)
class Config:
    week_start: str
    timezone: str
    anchor_date: date
    url_token: str
    people: tuple[str, ...]
    chores: tuple[Chore, ...]


def load_config(path) -> Config:
    """Parse and validate the config file at `path`; raise on anything bad."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ImproperlyConfigured(
            f"Cannot read config file {path}: {exc}"
        ) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ImproperlyConfigured(
            f"Config file {path} is not valid YAML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ImproperlyConfigured(
            f"{path}: top level must be a mapping of config keys"
        )
    unknown = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown:
        raise ImproperlyConfigured(f"{path}: unknown keys: {', '.join(unknown)}")
    missing = sorted(_TOP_LEVEL_KEYS - set(data))
    if missing:
        raise ImproperlyConfigured(f"{path}: missing keys: {', '.join(missing)}")

    return Config(
        week_start=_week_start(data["week_start"]),
        timezone=_timezone(data["timezone"]),
        anchor_date=_anchor_date(data["anchor_date"]),
        url_token=_url_token(data["url_token"]),
        people=_people(data["people"]),
        chores=_chores(data["chores"]),
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """The household config, loaded from settings.CHORES_CONFIG_PATH.

    Called once at startup by ChoresConfig.ready(), so a missing or invalid
    file crashes the process loudly instead of surfacing mid-request.
    """
    return load_config(settings.CHORES_CONFIG_PATH)


def _week_start(value):
    if value not in VALID_WEEK_STARTS:
        raise ImproperlyConfigured(
            f'week_start must be "monday" (the only supported value for now),'
            f" got {value!r}"
        )
    return value


def _timezone(value):
    if not isinstance(value, str):
        raise ImproperlyConfigured(f"timezone must be an IANA tz name, got {value!r}")
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        raise ImproperlyConfigured(
            f"timezone {value!r} is not a valid IANA tz name"
        ) from None
    return value


def _anchor_date(value):
    # YAML parses a bare YYYY-MM-DD scalar into a datetime.date already; a
    # string needs parsing (JSON-style configs). A datetime is rejected: the
    # anchor names which period is period zero and its time-of-day is
    # meaningless (decision doc).
    if isinstance(value, datetime):
        raise ImproperlyConfigured(
            "anchor_date must be a plain calendar date (YYYY-MM-DD),"
            " with no time component"
        )
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ImproperlyConfigured(
        f"anchor_date must be an ISO 8601 date (YYYY-MM-DD), got {value!r}"
    )


def _url_token(value):
    if not isinstance(value, str) or not value.strip():
        raise ImproperlyConfigured("url_token must be a non-empty string")
    return value


def _people(value):
    if not isinstance(value, list) or not value:
        raise ImproperlyConfigured("people must be a non-empty list of names")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ImproperlyConfigured(
                f"people entries must be non-empty strings, got {item!r}"
            )
    duplicates = sorted({name for name in value if value.count(name) > 1})
    if duplicates:
        raise ImproperlyConfigured(
            f"duplicate people names: {', '.join(duplicates)}"
        )
    return tuple(value)


def _chores(value):
    if not isinstance(value, list):
        raise ImproperlyConfigured(
            "chores must be a list of {name, period, offset} entries"
        )
    chores = []
    seen = set()
    for i, item in enumerate(value):
        where = f"chores[{i}]"
        if not isinstance(item, dict):
            raise ImproperlyConfigured(
                f"{where} must be a mapping with name, period and offset,"
                f" got {item!r}"
            )
        unknown = sorted(set(item) - _CHORE_KEYS)
        if unknown:
            raise ImproperlyConfigured(
                f"{where}: unknown keys: {', '.join(unknown)}"
            )
        missing = sorted(_CHORE_KEYS - set(item))
        if missing:
            raise ImproperlyConfigured(
                f"{where}: missing keys: {', '.join(missing)}"
            )
        name = item["name"]
        if not isinstance(name, str) or not name.strip():
            raise ImproperlyConfigured(
                f"{where}: name must be a non-empty string, got {name!r}"
            )
        if name in seen:
            raise ImproperlyConfigured(f"duplicate chore name: {name}")
        seen.add(name)
        period = item["period"]
        if period not in VALID_PERIODS:
            raise ImproperlyConfigured(
                f"{where} ({name}): unknown period {period!r};"
                f" expected one of {', '.join(VALID_PERIODS)}"
            )
        offset = item["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise ImproperlyConfigured(
                f"{where} ({name}): offset must be an integer, got {offset!r}"
            )
        chores.append(Chore(name=name, period=period, offset=offset))
    return tuple(chores)
