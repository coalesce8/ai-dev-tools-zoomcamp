# Decision: Week Boundary, Timezone, and Anchor Date

Status: settled 2026-09-06. Unblocks all date code (tasks 2, 3, and everything
downstream). This document is the single source of truth for how the app
converts a moment in time into a rotation period.

## The rule

**Weeks start on Monday** (ISO 8601). A weekly period runs Monday 00:00
through Sunday 24:00.

**All date arithmetic happens in `Europe/London`.** There is exactly one
rotation clock, and it is the household's wall clock — not the viewer's.
Consequences:

- A period flips at midnight London time, full stop. A housemate checking from
  another timezone on their Sunday night sees whatever period is current *in
  London*. There is no per-viewer rendering of period boundaries.
- DST (GMT ↔ BST) is handled by the IANA tz database. Days are civil
  (wall-clock) days in `Europe/London`; periods are midnight-to-midnight local
  time, so a period boundary never falls at 01:00 or 23:00 around a clock
  change.

**Monthly periods are calendar months** in `Europe/London`: the 1st 00:00
through the last day 24:00. Month lengths vary; the engine counts whole
months, never 30-day approximations.

## Config fields

The config format (implemented in task 2) carries these three fields:

```yaml
week_start: monday        # lowercase day name; only "monday" is valid for now,
                          # but the engine must read it from config, not hardcode it
timezone: Europe/London   # IANA tz database name
anchor_date: 2026-09-01   # ISO 8601 calendar date, interpreted in `timezone`
```

## Anchor date semantics

`anchor_date: 2026-09-01` — the period counter reads zero for the periods
containing the launch month.

- **Weekly chores:** period index 0 is the week containing the anchor date
  (Mon 2026-08-31 – Sun 2026-09-06). `periods_elapsed` counts whole weeks
  between the Monday of the anchor week and the Monday of the date's week.
- **Monthly chores:** period index 0 is September 2026. `periods_elapsed`
  counts whole calendar months between the anchor's month and the date's
  month.
- Dates before the anchor produce negative indices; the modulo in the
  assignee formula is a true mathematical modulo (result always in
  `0 .. len(people)-1`), so the rotation extrapolates backwards cleanly.

The anchor is a plain date, not a datetime: it names *which* period is period
zero, and its time-of-day is meaningless. The engine must never compare
datetimes against it directly.

## What this settles

- No ambiguity at period edges: "whose turn" at any instant is determined by
  converting that instant to `Europe/London`, taking the calendar date, and
  counting whole periods from the anchor.
- No viewer-relative behaviour to test: two housemates in different timezones
  always see the same assignee for the same instant.
- The one remaining household-specific choice — the concrete anchor — is set
  here for launch; task 11 (seed config) uses this value.
