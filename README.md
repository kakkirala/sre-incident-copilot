# SRE Incident Copilot

A local AI assistant for the full incident lifecycle: **alert → cause → fix → learn.**

Paste an alert, and it suggests a likely cause plus one safe runbook step.
Paste a pile of alerts, and it triages them. Paste logs, and it ranks the
root causes. Paste a cause, and it writes a remediation plan. Paste a
timeline, and it writes the postmortem. At every step, **nothing runs until
an engineer approves — and in v1, approval only records the decision.**

## The four use cases

| # | Use case | What it does | Code |
|---|----------|--------------|------|
| 1 | Alert triage | Groups duplicates, scores severity (P1–P4), suggests the owner team, worst first, with a noise-removed % | `triage.py` |
| 2 | Root cause analysis | Incident + logs + deploys in → ranked causes with quoted log evidence, confidence, and a verifying "Check next" each | `rca.py` |
| 3 | Guided remediation runbook | Read-only checks first, ONE proposed fix (flagged NEEDS APPROVAL), Risk, true Rollback (or honest "No rollback possible" + smaller blast radius), Dry-run preview | `runbook.py` |
| 4 | Incident postmortem | Timeline in → status update, executive summary, and a blameless postmortem with action items (9 sections, markdown) | `postmortem.py` |

Plus the original v1 agent (`main.py`): a LangGraph flow
`parse_alert → diagnose → recommend` that turns one alert into a cause and
one safe step — and a live metrics dashboard in the web UI (CPU, memory,
disk read/write, network sent/received, collected from the machine it runs
on, with HEALTHY vs BREACHING counts).

See `USE-CASES.md` for the roadmap, the metrics each use case practices
(alerts/day, MTTD, MTTR, postmortem time), and the golden rule.

## Safety rule (v1)

- **Diagnose / Triage / RCA / Postmortem:** read-only analysis. Nothing executes.
- **Runbook:** DRY-RUN ONLY. The plan is written, never run. Approve / Escalate
  buttons record the decision; they do not execute anything.
- **Human approval before ANY automated remediation. No exceptions.**

## Stack

- Python, Flask (web UI on port 5003)
- LangGraph + LangChain-Ollama, local model `llama3.2` via Ollama
- psutil for live machine metrics
- No API keys, no cloud calls: everything runs on your own machine.

## Run it

Prerequisites: Python 3.13, [Ollama](https://ollama.com) with the model
pulled (`ollama pull llama3.2`).

```powershell
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5003

CLI version of the v1 agent:

```powershell
python main.py
```

## Project structure

```
main.py         v1 LangGraph agent (parse → diagnose → recommend)
app.py          Flask web UI: Diagnose, Triage, RCA, Runbook, Postmortem, Live Metrics
triage.py       use case #1: dedup + severity + owner
rca.py          use case #2: ranked causes from incident + logs + deploys
runbook.py      use case #3: guided remediation plan (dry-run only)
postmortem.py   use case #4: blameless postmortem generator
USE-CASES.md    roadmap + metrics + golden rule
```

Generated outputs (`*_output.md`, `*_output.txt`) are git-ignored; the app
writes them locally when you use it.
