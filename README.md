# AI Dev Tools Zoomcamp

Coursework for the AI Dev Tools Zoomcamp. Each homework lives in its own
directory.

## hw1 — Household Chore Rotation

A Django app that answers "whose turn is it?" for household chores. The
guiding premise: the hard problem is adoption, not features, so every
decision optimises for the least motivated housemate having to do the least
possible.

The schedule is a **pure function of the date and a config file** — nothing
about who owes what is stored:

```
assignee_index = (periods_elapsed(chore.period) + chore.offset) % len(people)
```

Design highlights (full spec: `hw1/_docs/plan.md`):

- **Rotation advances on time, not completion** — a new period means a new
  assignee regardless of whether the last one did it; the rotation cannot
  deadlock on one person's inaction.
- **Completion is logged, never enforced** — ticking a chore appends a row to
  an append-only log. No debt maths, no nagging.
- **Swaps are overrides, not mutations** — "Sam takes my week" writes one
  override record per (chore, period); the computed schedule is never
  mutated.
- **Shared link, no accounts** — access control is an unguessable URL token;
  identity comes from the schedule itself.
- **Config file, no admin UI** — people and chores live in `chores.yaml`;
  changes are an edit and a redeploy.

### Layout

| Path | What it is |
|---|---|
| `hw1/chores.yaml` | People, chores, periods, offsets, timezone, URL token |
| `hw1/chores/engine.py` | Rotation engine — pure stdlib functions, no Django, no I/O |
| `hw1/chores/config.py` | Config loader/validator, fails loudly at startup |
| `hw1/chores/models.py` | `CompletionLog` (append-only ticks) and `SwapOverride` |
| `hw1/rotation/` | Django project settings |
| `hw1/_docs/` | Spec (`plan.md`), task backlog (`tasks.md`), decision records |

Date rules: weeks start Monday, all date arithmetic runs in
`Europe/London`, anchor date 2026-09-01
(`hw1/_docs/decision-week-boundary-timezone.md`).

### Run it

```sh
cd hw1
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test       # engine, config, and model tests
python manage.py runserver
```

### Status

Done: week-boundary decision, config loader, rotation engine, completion log
model, swap override model. In progress: schedule service (read path), main
page, tick endpoint, swap entry, URL gating, seed config, deployment.

The backlog is tracked in
[GitHub issues](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues);
`hw1/_docs/tasks.md` maps issues to build order.
