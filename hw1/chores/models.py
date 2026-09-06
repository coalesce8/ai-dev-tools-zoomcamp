"""Housemate-written state: the completion log and swap overrides.

The schedule itself is a pure function of the date and the config file
(_docs/plan.md); these two tables are the only stored exceptions, and both
are layered on top of the computation at read time — the computed schedule
is never mutated.

CompletionLog is the append-only history of ticks: someone did chore X for
period Y. SwapOverride is the release valve for "Sam takes my week": one row
per (chore, period) naming the replacement assignee.

Rows are keyed on (chore_name, period_start) with plain strings and dates,
not foreign keys, because people and chores live in the config file, never
the database. period_start is a calendar date in the config timezone (the
Monday for a weekly chore, the 1st for a monthly one). The engine's period
index is derivable from it via periods_elapsed(), while the date keeps the
records meaningful even if the anchor date ever changes.
"""

from django.db import models
from django.utils import timezone


class CompletionLog(models.Model):
    """One tick: `done_by` completed chore `chore_name` for the period
    starting on `period_start`.

    Append-only: re-ticking the same (chore, period) adds another row
    rather than overwriting, so the log stays an honest record of what
    people told it.
    """

    chore_name = models.CharField(max_length=200)
    period_start = models.DateField()
    done_by = models.CharField(max_length=200)
    logged_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-logged_at"]
        indexes = [
            # The read path's hot query: "is chore X ticked for period Y?"
            models.Index(fields=["chore_name", "period_start"]),
        ]

    def __str__(self):
        return f"{self.chore_name} ({self.period_start}): {self.done_by}"


class SwapOverride(models.Model):
    """`covered_by` takes over chore `chore_name` for the period starting on
    `period_start`, replacing whoever the computed schedule assigns.

    Keyed on (chore, period): at most one row per pair, so the table always
    holds exactly the overrides in force — a re-swap of the same period is
    the write path replacing this row, not a second one. Read path: compute
    the schedule, then apply any override on top.
    """

    chore_name = models.CharField(max_length=200)
    period_start = models.DateField()
    covered_by = models.CharField(max_length=200)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["period_start", "chore_name"]
        constraints = [
            # One override per (chore, period); the unique index doubles as
            # the read path's "is chore X swapped for period Y?" lookup.
            models.UniqueConstraint(
                fields=["chore_name", "period_start"],
                name="unique_swap_per_chore_period",
            ),
        ]

    def __str__(self):
        return f"{self.chore_name} ({self.period_start}): {self.covered_by}"
