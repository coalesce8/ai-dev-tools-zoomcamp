# Task Backlog — Household Chore Rotation

The backlog now lives in GitHub issues:
<https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues>

Tasks below are in build order; the spec terms (rotation engine, override,
completion log, anchor date) are defined in `_docs/plan.md`.

| Task | Issue | Status |
|---|---|---|
| Settle the week-boundary and timezone decision | [#2](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/2) | ✅ done |
| Config file loader | [#3](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/3) | ✅ done |
| Rotation engine | [#4](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/4) | ✅ done |
| Completion log model | [#5](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/5) | ✅ done |
| Swap override model | [#1](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/1) | open |
| Schedule service (read path) | [#6](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/6) | open |
| Main page | [#7](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/7) | open |
| Tick endpoint | [#8](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/8) | open |
| Swap entry | [#9](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/9) | open |
| Unguessable URL gating | [#10](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/10) | open |
| Seed config | [#11](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/11) | open |
| Deployment | [#12](https://github.com/coalesce8/ai-dev-tools-zoomcamp/issues/12) | open |

## Notes

- The plan says "exactly one write action" yet also has swaps writing override
  records; #8 and #9 resolve that as tick = the routine write, swap = the
  exceptional second write.
- Issue numbers don't match build order: #1 (swap override model) was created
  out of turn. Each issue title is now prefixed with its build-order task
  number ("Task 5: Swap override model"); the table above remains the source
  of truth for ordering.
- The week-boundary decision (#2) is settled — Monday week start, date math in
  `Europe/London`, anchor date 2026-09-01, recorded in
  `_docs/decision-week-boundary-timezone.md` — so nothing remains blocked.
