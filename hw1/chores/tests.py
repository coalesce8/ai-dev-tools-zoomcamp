import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone as dj_timezone

from . import engine
from .config import get_config, load_config
from .models import CompletionLog

VALID_CONFIG = """\
week_start: monday
timezone: Europe/London
anchor_date: 2026-09-01
url_token: test-token
people:
  - Alex
  - Sam
  - Jo
chores:
  - name: kitchen
    period: weekly
    offset: 0
  - name: fridge
    period: monthly
    offset: 1
"""


class LoadConfigTests(SimpleTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def write_config(self, text):
        path = Path(self.tmpdir.name) / "config.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def load(self, text):
        return load_config(self.write_config(text))

    def test_valid_config_loads(self):
        config = self.load(VALID_CONFIG)
        self.assertEqual(config.week_start, "monday")
        self.assertEqual(config.timezone, "Europe/London")
        self.assertEqual(config.anchor_date, date(2026, 9, 1))
        self.assertEqual(config.url_token, "test-token")
        self.assertEqual(config.people, ("Alex", "Sam", "Jo"))
        self.assertEqual([c.name for c in config.chores], ["kitchen", "fridge"])
        self.assertEqual(config.chores[0].period, "weekly")
        self.assertEqual(config.chores[1].offset, 1)

    def test_daily_period_accepted(self):
        config = self.load(VALID_CONFIG.replace("period: weekly", "period: daily"))
        self.assertEqual(config.chores[0].period, "daily")

    def test_anchor_date_as_quoted_string_accepted(self):
        config = self.load(VALID_CONFIG.replace("2026-09-01", '"2026-09-01"'))
        self.assertEqual(config.anchor_date, date(2026, 9, 1))

    def test_unknown_period_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("period: weekly", "period: yearly"))

    def test_duplicate_people_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("  - Jo\n", "  - Sam\n"))

    def test_duplicate_chore_names_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("name: fridge", "name: kitchen"))

    def test_missing_offset_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("    offset: 0\n", ""))

    def test_non_integer_offset_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("offset: 0", "offset: first"))

    def test_missing_top_level_key_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("url_token: test-token\n", ""))

    def test_unknown_top_level_key_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG + "anchr_date: 2026-09-01\n")

    def test_unknown_chore_key_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("offset: 0", "offest: 0"))

    def test_invalid_timezone_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("Europe/London", "Europe/Narnia"))

    def test_non_monday_week_start_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("week_start: monday", "week_start: sunday"))

    def test_anchor_date_with_time_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("2026-09-01", "2026-09-01T12:00:00"))

    def test_empty_people_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("  - Alex\n  - Sam\n  - Jo\n", "  []\n"))

    def test_missing_file_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            load_config(Path(self.tmpdir.name) / "does-not-exist.yaml")

    def test_get_config_uses_settings_path(self):
        path = self.write_config(VALID_CONFIG)
        get_config.cache_clear()
        self.addCleanup(get_config.cache_clear)
        with override_settings(CHORES_CONFIG_PATH=path):
            config = get_config()
        self.assertEqual(config.people, ("Alex", "Sam", "Jo"))


LONDON = ZoneInfo("Europe/London")
ANCHOR = date(2026, 9, 1)  # a Tuesday; anchor week is Mon 2026-08-31 – Sun 2026-09-06
TZ = "Europe/London"


class PeriodsElapsedTests(SimpleTestCase):
    def test_anchor_week_is_weekly_period_zero(self):
        for day in (date(2026, 8, 31), date(2026, 9, 1), date(2026, 9, 6)):
            with self.subTest(day=day):
                self.assertEqual(engine.periods_elapsed("weekly", day, anchor=ANCHOR), 0)

    def test_weekly_counts_whole_weeks_between_week_mondays(self):
        cases = {
            date(2026, 9, 7): 1,  # next Monday
            date(2026, 9, 13): 1,  # the Sunday after
            date(2026, 8, 30): -1,  # Sunday before the anchor week
            date(2026, 8, 24): -1,  # the Monday before
            date(2027, 8, 30): 52,  # exactly 364 days after the anchor Monday
            date(2025, 9, 1): -52,
        }
        for day, expected in cases.items():
            with self.subTest(day=day):
                self.assertEqual(
                    engine.periods_elapsed("weekly", day, anchor=ANCHOR), expected
                )

    def test_anchor_month_is_monthly_period_zero(self):
        for day in (date(2026, 9, 1), date(2026, 9, 30)):
            with self.subTest(day=day):
                self.assertEqual(
                    engine.periods_elapsed("monthly", day, anchor=ANCHOR), 0
                )

    def test_monthly_counts_whole_calendar_months(self):
        cases = {
            date(2026, 10, 1): 1,
            date(2026, 8, 31): -1,
            date(2027, 9, 1): 12,
            date(2025, 9, 1): -12,
            # Short months count as whole months; day-of-month is irrelevant.
            date(2027, 2, 1): 5,
            date(2027, 2, 28): 5,
        }
        for day, expected in cases.items():
            with self.subTest(day=day):
                self.assertEqual(
                    engine.periods_elapsed("monthly", day, anchor=ANCHOR), expected
                )

    def test_daily_counts_days(self):
        self.assertEqual(engine.periods_elapsed("daily", ANCHOR, anchor=ANCHOR), 0)
        self.assertEqual(
            engine.periods_elapsed("daily", date(2026, 9, 2), anchor=ANCHOR), 1
        )
        self.assertEqual(
            engine.periods_elapsed("daily", date(2026, 8, 31), anchor=ANCHOR), -1
        )

    def test_unknown_period_rejected(self):
        with self.assertRaises(ValueError):
            engine.periods_elapsed("yearly", ANCHOR, anchor=ANCHOR)

    def test_non_monday_week_start_rejected(self):
        with self.assertRaises(ValueError):
            engine.periods_elapsed("weekly", ANCHOR, anchor=ANCHOR, week_start="sunday")


class PeriodBoundsTests(SimpleTestCase):
    def test_weekly_bounds_are_monday_midnights(self):
        start, end = engine.period_bounds("weekly", date(2026, 9, 2), timezone=TZ)
        self.assertEqual(start, datetime(2026, 8, 31, tzinfo=LONDON))
        self.assertEqual(end, datetime(2026, 9, 7, tzinfo=LONDON))
        # September in London is BST (UTC+1).
        self.assertEqual(start.utcoffset(), timedelta(hours=1))

    def test_weekly_bounds_span_dst_change(self):
        # BST begins 2026-03-29: the week Mon 23 – Sun 29 March starts in GMT
        # and ends in BST, with both bounds still at local midnight.
        start, end = engine.period_bounds("weekly", date(2026, 3, 25), timezone=TZ)
        self.assertEqual(start, datetime(2026, 3, 23, tzinfo=LONDON))
        self.assertEqual(end, datetime(2026, 3, 30, tzinfo=LONDON))
        self.assertEqual(start.utcoffset(), timedelta(0))
        self.assertEqual(end.utcoffset(), timedelta(hours=1))

    def test_monthly_bounds(self):
        start, end = engine.period_bounds("monthly", date(2026, 9, 15), timezone=TZ)
        self.assertEqual(start, datetime(2026, 9, 1, tzinfo=LONDON))
        self.assertEqual(end, datetime(2026, 10, 1, tzinfo=LONDON))

    def test_monthly_bounds_cross_year_end(self):
        start, end = engine.period_bounds("monthly", date(2026, 12, 20), timezone=TZ)
        self.assertEqual(start, datetime(2026, 12, 1, tzinfo=LONDON))
        self.assertEqual(end, datetime(2027, 1, 1, tzinfo=LONDON))

    def test_leap_day_inside_february_bounds(self):
        start, end = engine.period_bounds("monthly", date(2028, 2, 29), timezone=TZ)
        self.assertEqual(start, datetime(2028, 2, 1, tzinfo=LONDON))
        self.assertEqual(end, datetime(2028, 3, 1, tzinfo=LONDON))

    def test_daily_bounds(self):
        start, end = engine.period_bounds("daily", date(2026, 9, 1), timezone=TZ)
        self.assertEqual(start, datetime(2026, 9, 1, tzinfo=LONDON))
        self.assertEqual(end, datetime(2026, 9, 2, tzinfo=LONDON))


class AssigneeIndexTests(SimpleTestCase):
    def test_rotates_through_people_week_by_week(self):
        # Three people, weekly chore, offset 0: the index cycles 0, 1, 2, 0.
        cases = {
            date(2026, 9, 1): 0,
            date(2026, 9, 7): 1,
            date(2026, 9, 14): 2,
            date(2026, 9, 21): 0,
        }
        for day, expected in cases.items():
            with self.subTest(day=day):
                self.assertEqual(
                    engine.assignee_index("weekly", 0, 3, day, anchor=ANCHOR), expected
                )

    def test_offset_shifts_starting_assignee(self):
        self.assertEqual(
            engine.assignee_index("weekly", 1, 3, date(2026, 9, 1), anchor=ANCHOR), 1
        )

    def test_monthly_rotation_with_offset(self):
        # A monthly chore with offset 1 (like the seeded fridge) and 3 people.
        cases = {
            date(2026, 9, 10): 1,
            date(2026, 10, 10): 2,
            date(2026, 11, 10): 0,
        }
        for day, expected in cases.items():
            with self.subTest(day=day):
                self.assertEqual(
                    engine.assignee_index("monthly", 1, 3, day, anchor=ANCHOR),
                    expected,
                )

    def test_negative_indices_use_true_modulo(self):
        # The week before the anchor week has period index -1, which must
        # wrap to the last person rather than produce a negative index.
        self.assertEqual(
            engine.assignee_index("weekly", 0, 3, date(2026, 8, 24), anchor=ANCHOR), 2
        )

    def test_far_future(self):
        # 2126-08-31 is 5217 whole weeks after the anchor week, and
        # 5217 % 3 == 0 — the rotation extrapolates arbitrarily far forward.
        self.assertEqual(
            engine.periods_elapsed("weekly", date(2126, 8, 31), anchor=ANCHOR), 5217
        )
        self.assertEqual(
            engine.assignee_index("weekly", 0, 3, date(2126, 8, 31), anchor=ANCHOR), 0
        )

    def test_far_past(self):
        # September 1926 is exactly 1200 months before the anchor month.
        self.assertEqual(
            engine.periods_elapsed("monthly", date(1926, 9, 15), anchor=ANCHOR), -1200
        )
        self.assertEqual(
            engine.assignee_index("monthly", 1, 3, date(1926, 9, 15), anchor=ANCHOR), 1
        )
        # 2609 whole weeks before the anchor week; -2609 % 3 == 1.
        self.assertEqual(
            engine.assignee_index("weekly", 0, 3, date(1976, 8, 30), anchor=ANCHOR), 1
        )

    def test_empty_people_rejected(self):
        with self.assertRaises(ValueError):
            engine.assignee_index("weekly", 0, 0, ANCHOR, anchor=ANCHOR)


class LocalDateTests(SimpleTestCase):
    def test_converts_instant_to_household_timezone(self):
        # 23:30 UTC on Sun 2026-09-06 is already Mon 00:30 in London (BST);
        # 22:30 UTC is still Sunday night there.
        self.assertEqual(
            engine.local_date(datetime(2026, 9, 6, 23, 30, tzinfo=timezone.utc), TZ),
            date(2026, 9, 7),
        )
        self.assertEqual(
            engine.local_date(datetime(2026, 9, 6, 22, 30, tzinfo=timezone.utc), TZ),
            date(2026, 9, 6),
        )

    def test_weekly_period_flips_at_midnight_london(self):
        # One rotation clock: the weekly index advances at midnight London,
        # regardless of where the instant is viewed from.
        before = engine.local_date(datetime(2026, 9, 6, 22, 59, tzinfo=timezone.utc), TZ)
        after = engine.local_date(datetime(2026, 9, 6, 23, 0, tzinfo=timezone.utc), TZ)
        self.assertEqual(engine.periods_elapsed("weekly", before, anchor=ANCHOR), 0)
        self.assertEqual(engine.periods_elapsed("weekly", after, anchor=ANCHOR), 1)

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            engine.local_date(datetime(2026, 9, 1), TZ)


class CompletionLogTests(TestCase):
    def test_entry_round_trips(self):
        CompletionLog.objects.create(
            chore_name="kitchen",
            period_start=date(2026, 8, 31),  # Monday of the anchor week
            done_by="Alex",
        )
        entry = CompletionLog.objects.get()
        self.assertEqual(entry.chore_name, "kitchen")
        self.assertEqual(entry.period_start, date(2026, 8, 31))
        self.assertEqual(entry.done_by, "Alex")
        self.assertEqual(
            str(entry), "kitchen (2026-08-31): Alex"
        )

    def test_logged_at_defaults_to_now(self):
        before = dj_timezone.now()
        entry = CompletionLog.objects.create(
            chore_name="fridge", period_start=date(2026, 9, 1), done_by="Sam"
        )
        self.assertGreaterEqual(entry.logged_at, before)
        self.assertLessEqual(entry.logged_at, dj_timezone.now())

    def test_same_chore_and_period_can_be_ticked_twice(self):
        # The log is append-only history, not a uniqueness-enforced state:
        # a second tick adds a row rather than failing or overwriting.
        for name in ("Alex", "Sam"):
            CompletionLog.objects.create(
                chore_name="kitchen", period_start=date(2026, 8, 31), done_by=name
            )
        self.assertEqual(
            CompletionLog.objects.filter(
                chore_name="kitchen", period_start=date(2026, 8, 31)
            ).count(),
            2,
        )

    def test_ordered_newest_first(self):
        older = CompletionLog.objects.create(
            chore_name="kitchen", period_start=date(2026, 8, 31), done_by="Alex"
        )
        newer = CompletionLog.objects.create(
            chore_name="fridge", period_start=date(2026, 9, 1), done_by="Jo"
        )
        self.assertEqual(list(CompletionLog.objects.all()), [newer, older])
