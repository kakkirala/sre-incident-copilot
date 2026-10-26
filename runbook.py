"""Use case #3: runbook automation & guided remediation.

This is the use case Boss put LAST on purpose: it is the one that touches
real systems, so it needs the most safety design. V1 rule, stated loudly
on the page: DRY-RUN ONLY. This module writes a plan, it never runs one.

Given an incident + a confirmed cause, the local model builds:
  1. Read-only checks FIRST (safe things to look at before any fix).
  2. One proposed fix, written out exactly.
  3. Risk: what could go wrong.
  4. Rollback: how to undo the fix.
  5. Dry-run preview: what a dry run would show, without changing anything.

Approval (Approve / Escalate on the page) only RECORDS the decision,
through the same /decision endpoint as Diagnose. Nothing executes.
"""

from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2", temperature=0.3)


def build_runbook(incident, cause):
    prompt = (
        "You are an SRE writing a guided remediation runbook. This is a PLAN "
        "ONLY — nothing you write will be executed by this page.\n\n"
        "Safety rules:\n"
        "- Read-only checks come FIRST, before any fix.\n"
        "- Propose exactly ONE fix, written as the actual command or SQL "
        "— not a description of it. Two fixes bundled together is not "
        "acceptable; pick the single most important one.\n"
        "- Any destructive step (kill, restart, delete, scale, failover) must "
        "be flagged NEEDS APPROVAL.\n"
        "- Every fix gets a Risk (what could go wrong) and a Rollback. "
        "Rollback must UNDO the fix: restore the previous value, restart "
        "what was stopped, reconnect what was disconnected. Restating the "
        "fix is NOT a rollback. If the fix cannot be undone (a killed "
        "session cannot be un-killed), say so honestly — 'No rollback "
        "possible' — and shrink the blast radius instead: only sessions "
        "idle over X minutes, in small batches, excluding critical users.\n"
        "- End with a Dry-run preview that NAMES what would change: the "
        "list of sessions or objects that WOULD be affected, with counts, "
        "without touching them. A vague 'would show the current state' is "
        "not acceptable.\n"
        "- Do not echo the incident and cause inputs back at the end. End "
        "at the Dry-run preview.\n\n"
        "Return exactly this format:\n"
        "Runbook: <one-line title>\n\n"
        "READ-ONLY CHECKS FIRST (safe, run these before any fix):\n"
        "1. <check> — <what it tells you>\n"
        "2. <check> — <what it tells you>\n\n"
        "PROPOSED FIX (NEEDS APPROVAL):\n"
        "<exact step>\n\n"
        "RISK: <what could go wrong>\n\n"
        "ROLLBACK: <how to undo it>\n\n"
        "DRY-RUN PREVIEW: <what a dry run would show, without changing anything>\n\n"
        f"INCIDENT:\n{incident}\n\n"
        f"CONFIRMED CAUSE:\n{cause}\n"
    )
    return llm.invoke(prompt).content
