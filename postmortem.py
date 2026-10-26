"""Use case #4 - incident postmortem generator (local Ollama llama3.2).

Paste an incident timeline (or a Slack/Teams thread) and get:
  a short status update, an executive summary, and a blameless postmortem
  with action items, in markdown.

Rules the prompt enforces (v2, fixed 2026-10-26 after the first review):
  - Use ONLY facts from the timeline.
  - Status follows the LAST timeline event: if it says closed/stable,
    the incident is resolved. Never say "ongoing" after a closed event.
  - Root cause states the evidence-backed cause (the fix that worked
    points to the cause). "Not stated" only when the timeline gives no clue.
  - Every action item ends with Owner: TBD, Due: TBD unless named.
  - Duration is computed by subtracting first event time from last event
    time, and the math is shown. Never guess the number.
  - Never blame a person or a team. Blameless language only.
"""

from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2", temperature=0.3)

POSTMORTEM_PROMPT = """You are a senior SRE writing a blameless incident postmortem.
Use ONLY facts from the timeline below. Never blame a person or a team.
Write in markdown with exactly these sections:

## Status update
2-3 lines: what happened, and the current state taken from the LAST
timeline event ONLY. If the last event says the incident closed or is
stable, say it is resolved. Never say "ongoing" after a closed event.

## Executive summary
3-5 lines for leadership: service, impact, cause, resolution.

## Timeline
Repeat the timeline events as a clean bullet list, in order.

## Root cause
State the most likely cause supported by the timeline evidence, in plain
language. If a fix resolved the incident, that fix points to the cause.
Use "Not stated" ONLY when the timeline gives no clue at all.

## Impact
Who/what was affected, with numbers from the timeline. For the duration,
subtract the first event time from the last event time yourself and show
the math, for example: 14:32 to 15:10 = 38 minutes. Never guess the number.

## What went well
Bullet list.

## What went wrong
Bullet list. Focus on process and systems, never people.

## Action items
Bullet list. EVERY item MUST end with "Owner: TBD, Due: TBD" unless the
timeline names an owner or a date. No exceptions, no bare items.

## Lessons learned
2-4 short bullets.

Timeline:
{timeline}
"""

SAMPLE_TIMELINE = """14:32 - Alert fired: payment-api p99 latency 8.2s (normal 0.4s), 5xx rate 12%.
14:35 - On-call engineer paged, acknowledged the alert.
14:40 - Checked dashboards: DB connection pool 100/100 in use, 240 queries waiting.
14:45 - No new deployment in the last 6 hours, ruled out a bad deploy.
14:50 - Killed long-running idle sessions and raised the pool temporarily.
15:02 - Latency back to 0.4s, 5xx rate back to 0%.
15:10 - Monitoring confirmed stable for 10 minutes, incident closed."""


def generate_postmortem(timeline: str) -> str:
    return llm.invoke(POSTMORTEM_PROMPT.format(timeline=timeline)).content
