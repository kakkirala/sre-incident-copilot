# SRE Incident Copilot — Use Cases (Roadmap)

Source: Boss, 2026-10-26. Together these four cover the full incident lifecycle:
alert → cause → fix → learn.

## 1. Alert triage and noise reduction

- **Business problem:** On-call engineers drown in duplicate or low-value alerts.
- **Build:** Feed sample alerts (JSON from Prometheus or Azure Monitor) into a script
  that groups duplicates, scores severity, and suggests the owner.
- **Copilot's role:** Generate the correlation logic and regex/dedup rules, and write
  unit tests.
- **Metric to practice:** Alerts reduced per day.
- **Status in our build:** BUILT & VERIFIED 2026-10-26 — triage.py + Triage
  section in the web UI (dedup in plain Python, P1–P4 severity, owner team,
  worst first, noise % shown).

## 2. Root cause analysis from logs and metrics

- **Business problem:** Finding the cause takes 30-60 minutes of digging through logs.
- **Build:** A tool that takes an incident window, pulls logs and recent deploys,
  and produces a ranked list of likely causes.
- **Copilot's role:** Write KQL/Splunk/PromQL queries, parse stack traces, and
  explain anomalies in plain language.
- **Metric:** Mean time to diagnose (MTTD).
- **Status in our build:** BUILT & VERIFIED 2026-10-26 — rca.py + RCA section
  (incident + logs + deploys in, ranked causes with quoted log evidence,
  confidence, and a verifying "Check next" each).

## 3. Runbook automation and guided remediation

- **Business problem:** Runbooks are outdated, and fixes are manual and error-prone.
- **Build:** Convert a text runbook (for example, "high CPU on pod" or
  "DB connection pool exhausted") into a script that runs safe, read-only checks
  first, then proposes a fix and asks for approval.
- **Copilot's role:** Generate the kubectl/Azure CLI/Python steps and add
  guardrails like dry-run mode and approval prompts.
- **Metric:** Mean time to resolve (MTTR).
- **Status in our build:** V1 WORKING (CLI, 2026-10-26) — parse → diagnose →
  recommend one safe step. Still to add: web UI, Approve / Edit / Escalate
  buttons, read-only checks first, dry-run mode.

## 4. Auto-generated incident summary and postmortem

- **Business problem:** Postmortems are slow to write and often skipped.
- **Build:** Take a Slack/Teams incident thread plus a timeline and generate a
  status update, an executive summary, and a blameless postmortem with action items.
- **Copilot's role:** Draft the templates, write the summarization prompts, and
  format the output as markdown or tickets.
- **Metric:** Time to publish a postmortem (hours instead of days).
- **Status in our build:** V1 WORKING (verified 2026-10-26 — all 9 sections generated from the sample timeline in seconds). V2 polish notes: status must follow the LAST timeline event (it wrongly said "ongoing" after a "closed" event); root cause should state the evidence-backed cause instead of dodging to "Not stated"; action items must carry Owner: TBD / Due: TBD; impact duration math to check (38 min, not 43).

## Build order (Boss's order — this wins)

1. **#4 first — easiest**, quick win: postmortem generator.
2. Then **#1** — triage/dedup.
3. Then **#2** — RCA.
4. **#3 last — needs the most safety design** (it touches real remediation).

## Practice plan

- Use a small sandbox (Docker or minikube) with a demo app — for example an
  online meal planner — and inject failures: a memory leak, a bad config deploy.
- The Copilot diagnoses the injected failure, end to end.
- **Golden rule, always: a human approval step before ANY automated remediation.**
  No exceptions, in every use case.

Prometheus proactive monitoring (trend warnings before alerts fire) plugs into
#1 and #2 once the web UI + local vitals are done.
