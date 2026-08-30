# Design council protocols

The conductor runs these through the Herdr execution policy in the parent skill and blocks when that path is unavailable. Subagents do not call each other.

## Shared: evidence phase (all protocols)

Before any council seat:

1. Write or update `var/<feature-name>/design-council/<session-slug>/brief.md` with:
   - Design question, constraints, options (if any)
   - Success criteria
2. **Mandatory** if third-party libraries or APIs are involved: assign one web-research responsibility per topic
3. **Mandatory** for repository behavior: assign repository exploration for affected areas
4. **Optional**: assign data or runtime evidence responsibilities when those facts matter
5. Append **Evidence summary** section to `brief.md` (bullet facts with sources)

Skip council if evidence phase finds the question is purely factual — answer from explorers and stop.

---

## Synthesize (default)

Cheapest. Use when 2–3 options exist and you need one merged recommendation.

| Step | Action                                                |
| ---- | ----------------------------------------------------- |
| 1    | Advocate responsibility — brief path; propose options |
| 2    | Critic responsibility — advocate output + brief       |
| 3    | Data-flow review responsibility — advocate + brief    |
| 4    | Chair responsibility — all seat outputs + brief       |

Optionally add a verification responsibility for the chair output.

---

## Debate

Use when tradeoffs are real and roles should argue (ownership, sync vs async, API shape).

| Round         | Tasks                                                                                                 |
| ------------- | ----------------------------------------------------------------------------------------------------- |
| 1 Independent | Parallel advocate, critic, and data-flow responsibilities; each sees **brief only**                   |
| 2 Cross-talk  | Parallel: each seat again with **summaries of the other two**; must engage disagreements              |
| 3 Tie-break   | Only if round 2 still BLOCK/UNSOUND vs APPROVE split — chair responsibility with transcript summaries |

Max **3** debate rounds total. Stop early if all seats CONCERNS or better with same recommendation.

Then the chair produces the final memo if it was not already done in round 3.

---

## Vote

Use when picking among labeled options (library A vs B, pattern X vs Y) after evidence.

| Step | Action                                                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Each option gets a short **anonymous** write-up: conductor merges advocate-style bullets into `Option A`, `Option B`, … in `brief.md` (no author names) |
| 2    | Judge responsibility — anonymous options only                                                                                                           |
| 3    | If close: second independent judge with the same anonymous pack                                                                                         |
| 4    | Chair responsibility — judge ranking + brief + dissent from any seat run earlier                                                                        |

Run the web-research responsibility before voting on external products or APIs.

---

## Critique

Stress-test one leading design (user or advocate pick).

| Step | Action                                                          |
| ---- | --------------------------------------------------------------- |
| 1    | Critic responsibility in **red-team** mode on candidate + brief |
| 2    | Data-flow review responsibility on the same candidate           |
| 3    | Chair responsibility — go/no-go with mitigations                |

---

## Verify (MAV)

Score one candidate answer; do not treat agreement as proof.

| Step | Action                                                          |
| ---- | --------------------------------------------------------------- |
| 1    | Verification responsibility on candidate + brief                |
| 2    | If WEAK/FAIL: record the critic findings and block the decision |

---

## Artifact layout

```text
var/<feature-name>/design-council/<session-slug>/
  brief.md
  round-1-advocate.md    # optional copies of seat outputs
  round-1-critic.md
  synthesis.md           # chair output
```

The conductor may save seat outputs to files to keep independent briefs small. Use only the repository's documented ignored artifact location, or an operating-system temporary directory when none exists.
