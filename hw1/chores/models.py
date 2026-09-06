"""The completion log: the app's only housemate-written state.

The schedule itself is a pure function of the date and the config file
(_docs/plan.md); this table is the one stored exception. A row records that
someone ticked a chore for a period — no debt maths, no enforcement, just
history so the household can have the conversation itself.

Rows are keyed on (chore_name, period_start) with plain strings and dates,
not foreign keys, because people and chores live in the config file, never
the database. period_start is a calendar date in the config timezone (the
Monday for a weekly chore, the 1st for a monthly one). The engine's period
index is derivable from it via periods_elapsed(), while the date keeps the
history meaningful even if the anchor date ever changes.
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
