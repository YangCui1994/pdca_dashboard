---
name: pdca-gate
description: Review raw work notes, daily plans, and task events against PDCA. Classify Plan/Do/Check/Act, detect whether Do entries are concrete actions or personal judgments, and produce repair suggestions.
---

# PDCA Gate

Use this skill when the user asks to review, clean, classify, or generate PDCA content for daily work, weekly work, task events, or project progress notes.

## Core Contract

Treat PDCA as an evidence discipline, not a writing format.

- `Plan`: an intended outcome, constraint, hypothesis, priority, or next action before execution.
- `Do`: a concrete action already performed by a specific actor on a specific object at a specific time or in a specific session.
- `Check`: an observation, measurement, comparison, result, feedback, or evidence after doing.
- `Act`: an adjustment, standardization, escalation, decision, or next-cycle change based on Check.

## Do Classification

Classify every claimed Do as one of:

- `true_do`: a concrete action happened and the statement includes enough object/result detail to verify it.
- `candidate_do`: an action probably happened, but time, object, result, or evidence is missing.
- `not_do`: the statement is a belief, interpretation, emotion, preference, plan, or conclusion rather than an action.

## Bias And Evidence Flags

Flag these issues when present:

- `bias_or_judgment`: the sentence asserts a cause, motive, quality, priority, or blame without evidence.
- `evidence_needed`: the sentence needs a number, artifact, link, screenshot, decision record, query, message, or file reference.
- `scope_unclear`: the task, object, owner, or time window is ambiguous.
- `next_action_missing`: the note cannot produce a concrete next action.

## Review Output

When reviewing user input, output:

```markdown
## PDCA 分类

| 原句 | 分类 | Do 级别 | 问题标记 | 理由 |
| --- | --- | --- | --- | --- |

## 需要改写的 Do

- 原句：
- 问题：
- 更好的写法：
- 需要补充的证据：

## 可执行下一步

- 下一步动作：
- 需要的上下文：
- 可验证产出物：
```

## Generation Rules

- Prefer concrete verbs: sent, opened, compared, wrote, tested, asked, changed, saved, reviewed.
- Avoid pretending judgments are actions.
- Keep personal feelings only as context, not as Do.
- If evidence is missing, ask for the smallest useful artifact.
- Keep the user moving: every review should end with one concrete next action.
