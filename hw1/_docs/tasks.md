# Task Backlog — Household Chore Rotation

Backlog for the v1 spec in `_docs/plan.md`; the terms below (rotation engine,
override, completion log, anchor date) are defined there. Tasks are listed
roughly in build order, but each is self-contained and can be picked up on its
own. Task 1 should go first — the plan forbids date code until it's settled.

## 1. Settle the week-boundary and timezone decision
Goal: Turn the plan's one open decision into a written, unambiguous rule.
Description: `plan.md` flags week start (Monday vs Sunday) and timezone behaviour as unsettled and blocks all date code on the answer. Decide for the household and record it in `_docs/`, including the fields the config format will carry: `week_start`, `timezone`, and the anchor date the rotation counts from. No production code in this task.

## 2. Config file loader
Goal: People and chores come from a version-controlled config file, never the database.
Description: Define and implement the config format (YAML or JSON): a people list, chores each with `period` (weekly/monthly, schema supports daily) and `offset`, plus `week_start`, `timezone`, anchor date, and the unguessable URL token. A loader module validates the file at startup and fails loudly on bad data (unknown period, duplicate names, missing offset). Cover with tests using fixture configs.

## 3. Rotation engine
Goal: Pure functions that answer "whose turn is it" for any chore and any date.
Description: Implement the plan's formula — `assignee_index = (periods_elapsed(chore.period) + chore.offset) % len(people)` — as a dependency-free module: periods elapsed since the anchor date, current period start/end for weekly and monthly periods, and the assignee for a chore on a given date. Honour the configured week start and timezone. Unit-test the boundaries: period edges, month lengths, and dates far forward and back.

## 4. Completion log model
Goal: A table recording that someone ticked a chore for a period.
Description: One Django model — chore key, period identifier (period index or start date), name of who did it, timestamp — plus its migration. This is the app's only housemate-written state; the schedule itself stays computed. Include a basic model test.

## 5. Swap override model
Goal: A table for "Sam takes my week" exceptions.
Description: One Django model keyed on (chore, period) storing the replacement name, plus its migration. Overrides are applied on top of the computed schedule at read time; the computed schedule is never mutated. Include a basic model test.

## 6. Schedule service (read path)
Goal: One function returning everything the main page needs for a date.
Description: Combine the rotation engine, swap overrides, and completion log into a service that, for a date, returns each chore's current period, the assignee with any override applied, and whether (and by whom) it's been ticked. It returns plain data structures so views stay thin. Test the override-wins-over-computed and ticked-state cases.

## 7. Main page
Goal: The single page housemates see.
Description: A view and template at the shared URL listing every chore with its current period dates, who it's on (post-override), a checkbox showing ticked state, and a name dropdown next to the checkbox defaulted to the assignee. Rendering only — the form posts to the tick endpoint built separately. Showing each period's dates matters so "which week is this" is never ambiguous.

## 8. Tick endpoint
Goal: The app's one routine write action.
Description: A POST endpoint taking (chore, period, name) that writes a completion log row and redirects back to the main page, with CSRF protection left on. Decide and document the re-tick policy — updating the existing row for that chore+period keeps the log idempotent. Test the write, the re-tick behaviour, and the redirect.

## 9. Swap entry
Goal: Let a housemate hand a period to someone else.
Description: Add the second and final write path: a small form on the main page ("X covers this period") that writes an override record for (chore, period). The displayed assignee updates through the existing read path — no schedule mutation. Test that the override takes effect and expires with its period.

## 10. Unguessable URL gating
Goal: The shared secret URL is the entire access control.
Description: Gate every housemate-facing route on the token from config — in the path or a query param — returning 404 (not 403) on mismatch so the URL's existence isn't confirmed. Keep Django admin outside the token scheme. Test the allowed and denied cases.

## 11. Seed config
Goal: Real household data the app launches with.
Description: Write the production config: the housemates, the weekly chores, and the monthly/quarterly ones (fridge clean-out, descaling, filters, bulk collection) where the plan says the real value is. Stagger offsets so monthly chores don't stack on one person in one month, and set the anchor date. No daily chores — the plan excludes them deliberately.

## 12. Deployment
Goal: The app reachable at its real, unguessable URL.
Description: Move the secret key and debug flag into environment settings, set ALLOWED_HOSTS, run migrations, and deploy behind a production server somewhere the household can reach. Confirm the plan's assumed workflow — config change = edit + redeploy — actually works end to end.

## 13. ICS calendar feed (v2)
Goal: Chores appear in the calendars housemates already check.
Description: A read-only endpoint emitting an `.ics` feed computed from the same rotation engine — one all-day event per chore period with the assignee — so people subscribe once. No new state. The plan defers this past v1, but pull it forward if the chore list grows past two or three monthly items.

## Notes

- The plan says "exactly one write action" yet also has swaps writing override records; tasks 8 and 9 resolve that as tick = the routine write, swap = the exceptional second write. Adjust task 9 if you read the plan differently.
- Task 1 blocks task 3 and everything downstream of it; the rest can interleave.
