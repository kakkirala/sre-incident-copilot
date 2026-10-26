"""Use case #2: RCA from logs + metrics.

Paste three things: (1) what the incident looks like, (2) log lines from
the incident window, (3) recent deploys/changes. The local model ranks
the likely causes by evidence, instead of guessing one answer.

Rules baked into the prompt (learned from the v1 diagnose and postmortem
runs): the top cause MUST cite specific log lines; "not stated" is not
an answer when the logs contain a clue; and deploys are ruled in or out
explicitly from the deploys box, not assumed.
"""

from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2", temperature=0.3)


def analyze_rca(incident, logs, deploys):
    prompt = (
        "You are an SRE doing root cause analysis. Rank the likely causes "
        "of this incident by the EVIDENCE, worst first.\n\n"
        "Rules:\n"
        "- Look for resource-exhaustion lines FIRST (pool 100/100, threads "
        "awaiting, connections exhausted, out of memory, disk full). These "
        "are the strongest clues and usually the top cause.\n"
        "- A timeout, a retry failure, or an error rate is a SYMPTOM, not a "
        "cause. Ask what made it happen (it timed out BECAUSE the pool was "
        "full) and rank the underlying cause, not the symptom.\n"
        "- The top cause MUST quote the specific log lines that support it.\n"
        "- Never answer 'not stated' when the logs contain a clue — name the "
        "evidence-backed cause instead.\n"
        "- Do the time math: compare each deploy time with the incident start "
        "time. A deploy hours before the incident is NOT recent and NOT "
        "within the incident window.\n"
        "- Never rank a cause in the top 3 AND rule it out in the same "
        "answer. If it is ruled out, it goes ONLY in 'Ruled out'.\n"
        "- Rule deploys in or out explicitly from the deploys box below. "
        "If it says no recent deploys, say a bad deploy is ruled out and why.\n"
        "- Each cause gets a confidence: High, Medium, or Low.\n"
        "- End each cause with one concrete 'Check next' step that would "
        "confirm or rule it out.\n"
        "- Your answer MUST start with exactly: Most likely: <cause>\n"
        "- Format is strict: exactly 3 numbered causes, then ONE 'Ruled out:' line at the end. Never number a ruled-out item (no '2. Ruled out:').\n"
        "- 'Ruled out' covers ONLY things named in the inputs (a deploy, a query, a service). Never invent ruled-out items like 'out of memory' or 'disk full' when no log mentions them.\n"
        "- 'Check next' must be a step that VERIFIES that cause: for pool exhaustion, find which sessions or queries hold the connections; for a slow query, check its explain plan. Never a vague 'verify if X changed recently'.\n"
        "- Every numbered item must be a cause with Evidence + Check next. If you have fewer than 3 real causes, say so in that cause's Evidence ('weaker evidence') \u2014 do not fill the list with ruled-out items.\n\n"

        "Return exactly this format:\n"
        "Most likely: <one line>\n\n"
        "1. <cause> (Confidence: High/Medium/Low)\n"
        "   Evidence: <log lines>\n"
        "   Check next: <concrete check>\n\n"
        "2. <cause> (Confidence: High/Medium/Low)\n"
        "   Evidence: <log lines>\n"
        "   Check next: <concrete check>\n\n"
        "3. <cause> (Confidence: High/Medium/Low)\n"
        "   Evidence: <log lines>\n"
        "   Check next: <concrete check>\n\n"
        "Ruled out: <what was ruled out and why>\n\n"
        f"INCIDENT:\n{incident}\n\n"
        f"LOGS:\n{logs}\n\n"
        f"RECENT DEPLOYS / CHANGES:\n{deploys}\n"
    )
    return llm.invoke(prompt).content
