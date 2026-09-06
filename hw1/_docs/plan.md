# Household Chore Rotation — v1 Spec

## Premise

The hard problem is adoption, not features. Every decision below optimises for the
least motivated housemate having to do the least possible. The app has exactly one
write action.

## Core model

The schedule is a **pure function of the date and a config file**. Nothing about who
owes what is stored.

```
assignee_index = (periods_elapsed(chore.period) + chore.offset) % len(people)
```

Consequences:

- No queue, no stored state, no sync conflicts, no migrations.
- Anyone's schedule is computable arbitrarily far forward or back.
- The rotation cannot deadlock on one person's inaction.

### Rotation advances on time, not completion

A new period means a new assignee regardless of whether the last one did it.

Rejected: completion-gated advance (one unreliable person blocks the whole queue) and
debt carry-over (doubles state complexity, and a running who-owes-whom tally is a
guilt mechanic that probably makes households feel worse — low confidence on the
behavioural half, high confidence on the complexity cost).

### Completion is logged, never enforced

A checkbox writes a row to a log. No debt maths, no nagging, no chasing. The history
exists so people can have the conversation themselves if they want to.

### Swaps are overrides, not mutations

"Sam takes my week" writes an override record keyed on (chore, period). The computed
schedule is never mutated. Read path: compute, then apply any override on top.

This is the release valve for travel, illness, and favours — the exception handling
that rotation tools normally die without.

## Access

**Shared link. No accounts.**

The rotation already supplies identity: if the box is ticked for a period, the
schedule says who it was assigned to. Accounts would only buy the gap between
*assigned* and *actually did*, and the swap override covers that case.

- Name dropdown next to the checkbox, defaulted to the assignee, one tap to change.
- Honour system. In a small household everyone can see the log; lying to it is
  socially self-defeating.
- Access control is the unguessable URL. Rotate it when someone moves out.

Explicitly not built: user table, sessions, invites, password reset. That is the
majority of the project and the friction that kills adoption on day three.

## Chores

Each chore carries its own `period`. Making period a field rather than a constant is a
few lines now and a rewrite of every date calculation later.

**Seeded with weekly and monthly. No daily chores.**

- Weekly is the workhorse.
- Monthly/quarterly is where the value is — fridge clean-out, descaling, filters,
  bulk collection. Nobody remembers these and no household norm covers them.
- Daily tasks (dishes, counters, tidying) are deliberately excluded. Rotation turns a
  norm — clean up after yourself — into a rule, and the rule is worse: the dishes sit
  there while three people walk past knowing it is Not Their Job. Daily wants a habit.
  The schema supports daily if a genuinely shared daily task appears.

**Stagger the offsets.** With four people, a monthly chore comes round every four
months, and several monthly chores can coincidentally land on the same person in the
same month. Set distinct starting offsets per chore at seed time. One-line decision
now, annoying to fix later.

## Notifications

**None in v1.**

Known tension: the monthly chores are the point, and "people check the link" fails
hardest there — nobody opens a chore app in a month they think is empty. Accepted
because an ICS feed is unusually cheap to defer (read-only endpoint off the same
formula, no new state, no change to anything above).

**v2: calendar feed.** Subscribe once, chores appear in the calendar people already
look at.

**Trigger to pull it forward:** if the chore list grows past two or three monthly
items, build the feed before launch. The more value sits in the rarely-due bucket, the
less "check the link" holds.

## Configuration

**Config file, no admin UI.** People and chores live in JSON/YAML; changes are an edit
and a redeploy.

The list changes maybe twice a year. CRUD screens for that are the classic v1
overbuild, and "who may delete a chore" is a question a no-accounts app should not
have to answer.

Cost: only the maintainer can change anything. In a house of three or four that is a
text message. Revisit if the maintainer is not the technical one or resents the
bottleneck.

## Surface area

| Thing | Storage |
|---|---|
| People, chores, periods, offsets | Config file |
| Schedule | Computed |
| Swaps | Override records |
| Completions | Log table |

Write endpoints: one (tick a chore). Everything else is derived.

## Decision — settled

**Week boundary and timezone.** Weeks start Monday; all date arithmetic runs in
`Europe/London`; anchor date 2026-09-01. Full rule and config fields:
`_docs/decision-week-boundary-timezone.md`.

## Out of scope for v1

Accounts, admin UI, notifications, debt tracking, points/gamification, daily chores,
per-person preferences, multi-household support.
