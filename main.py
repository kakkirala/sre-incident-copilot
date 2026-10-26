"""SRE Incident Copilot - LangGraph agent (local, Ollama llama3.2).

Paste an alert or log snippet, get:
  likely cause + reasoning + ONE safe runbook step.
Nothing runs by itself - the engineer approves first.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2", temperature=0.3)


class CopilotState(TypedDict):
    alert_text: str
    service: str
    symptom: str
    likely_cause: str
    reasoning: str
    recommended_step: str
    check_after: str


PARSE_PROMPT = """You are an SRE assistant. Read the alert or log below and pull out two facts in plain text, no markdown:
Service: the service or system name, or "unknown" if not shown.
Symptom: the main symptom in one short line (what is failing, with numbers if shown).

Alert:
{alert}
"""

DIAGNOSE_PROMPT = """You are a senior SRE. Given this service and symptom, write the most likely cause in plain text, no markdown.
First one short line: Likely cause.
Then 2-3 short lines: Reasoning (why this cause fits the symptom).

Service: {service}
Symptom: {symptom}
"""

RECOMMEND_PROMPT = """You are a senior SRE. Given the service, symptom and likely cause, recommend exactly ONE safe next runbook step in plain text, no markdown.
First one short line: Recommended step (safe to do, does not restart or delete anything in production).
Then one short line: Check after (what number or signal proves the step worked).

Service: {service}
Symptom: {symptom}
Likely cause: {cause}
"""


def parse_alert(state: CopilotState) -> dict:
    out = llm.invoke(PARSE_PROMPT.format(alert=state["alert_text"])).content
    service, symptom = "unknown", ""
    for line in out.splitlines():
        line = line.strip()
        if line.lower().startswith("service:"):
            service = line.split(":", 1)[1].strip()
        elif line.lower().startswith("symptom:"):
            symptom = line.split(":", 1)[1].strip()
    return {"service": service, "symptom": symptom or out.strip()}


def diagnose(state: CopilotState) -> dict:
    out = llm.invoke(
        DIAGNOSE_PROMPT.format(service=state["service"], symptom=state["symptom"])
    ).content
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    cause = lines[0] if lines else out.strip()
    reasoning = "\n".join(lines[1:]) if len(lines) > 1 else ""
    return {"likely_cause": cause, "reasoning": reasoning}


def recommend(state: CopilotState) -> dict:
    out = llm.invoke(
        RECOMMEND_PROMPT.format(
            service=state["service"],
            symptom=state["symptom"],
            cause=state["likely_cause"],
        )
    ).content
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    step = lines[0] if lines else out.strip()
    check = "\n".join(lines[1:]) if len(lines) > 1 else ""
    return {"recommended_step": step, "check_after": check}


graph = StateGraph(CopilotState)
graph.add_node("parse_alert", parse_alert)
graph.add_node("diagnose", diagnose)
graph.add_node("recommend", recommend)
graph.set_entry_point("parse_alert")
graph.add_edge("parse_alert", "diagnose")
graph.add_edge("diagnose", "recommend")
graph.add_edge("recommend", END)
agent = graph.compile()

SAMPLE_ALERT = """ALERT: payment-api p99 latency 8.2s (normal 0.4s), 5xx rate 12% for 15 minutes.
DB connection pool exhausted: 100/100 connections in use, 240 queries waiting.
No new deployment in the last 6 hours."""

if __name__ == "__main__":
    result = agent.invoke({"alert_text": SAMPLE_ALERT})
    text = (
        f"Service: {result['service']}\n"
        f"Symptom: {result['symptom']}\n"
        f"Likely cause: {result['likely_cause']}\n"
        f"Reasoning:\n{result['reasoning']}\n"
        f"Recommended step: {result['recommended_step']}\n"
        f"Check after:\n{result['check_after']}\n"
    )
    print(text)
    with open("sre_copilot_output.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved to sre_copilot_output.txt")
