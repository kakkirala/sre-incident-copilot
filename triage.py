"""Use case #1: alert triage & noise reduction.

Paste many alerts -> duplicates are grouped (the same alert seen many
times counts once) -> each UNIQUE alert gets a severity + owner team
from the local model -> worst first.

Dedup rule (plain Python, no model needed, so it never guesses wrong):
two alerts are the same when they match after lowercasing, removing
timestamps, and replacing measured VALUES (12%, 8.2s, 92%) with '#'.
Host names and service names are kept, so worker-3 and worker-4 stay apart.
"""

import re

from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2", temperature=0.3)

MAX_UNIQUE = 20


def _normalize(line):
    text = line.strip().lower()
    text = re.sub(r"\d{1,2}:\d{2}(:\d{2})?", "", text)  # timestamps
    text = re.sub(r"\d+(\.\d+)?\s*(%|ms|s|mb|gb|/s)", "#", text)  # measured values
    return re.sub(r"\s+", " ", text).strip()


def group_alerts(alerts_text):
    """Return (total, groups); groups = [{'text': first seen, 'count': n}]."""
    groups, order = {}, []
    total = 0
    for line in alerts_text.splitlines():
        line = line.strip()
        if not line:
            continue
        total += 1
        key = _normalize(line)
        if key in groups:
            groups[key]["count"] += 1
        else:
            groups[key] = {"text": line, "count": 1}
            order.append(key)
    return total, [groups[k] for k in order]


def _severity_rank(line):
    m = re.match(r"\s*-\s*\[(P[1-4])\]", line)
    if not m:
        return 4
    return {"P1": 0, "P2": 1, "P3": 2, "P4": 3}[m.group(1)]


def triage_alerts(alerts_text):
    total, groups = group_alerts(alerts_text)
    if not groups:
        return "No alerts found. Paste one alert per line."
    unique = groups[:MAX_UNIQUE]
    listed = "\n".join(
        f"{i + 1}. {g['text']} (seen {g['count']}x)" for i, g in enumerate(unique)
    )
    prompt = (
        "You are an SRE on-call triage assistant. Triage these UNIQUE alerts.\n"
        "For EACH alert, give: severity and owner team and a one-line reason.\n"
        "Severity rules:\n"
        "- P1 = users impacted NOW. Any user-facing or payment path with errors (5xx, failed checkouts) is P1.\n"
        "- P2 = degraded but users can still get through, P3 = warning (will become a problem), P4 = noise/info.\n"
        "Owner team rules: pick from what the alert itself names — a service (payment-api, checkout-service) -> Backend;\n"
        "a database or connection pool -> Database; a host, CPU, disk, or memory -> Platform;\n"
        "network words (DNS, packet loss, connectivity) -> Network. Use Unknown only when nothing fits.\n"
        "Reason rule: say WHY it matters (what breaks for users, what happens next) — never just repeat the alert.\n"
        "The (seen Nx) note is only a count for you — do NOT copy it into your line.\n"
        "Keep the alerts in the SAME ORDER and return one line per alert in exactly this format:\n"
        "- [P1] [Database] <alert text> — <reason>\n"
        "Return ONLY those lines, nothing else.\n\n"
        f"{listed}"
    )
    triaged = llm.invoke(prompt).content
    # Worst first: sort by the severity the model assigned (stable, so ties
    # keep the model's order). Also strip any "(seen Nx)" the model copied.
    lines = [
        re.sub(r"\s*\(seen \d+x\)", "", line)
        for line in triaged.splitlines()
        if line.strip()
    ]
    lines.sort(key=_severity_rank)
    reduced = total - len(groups)
    pct = round(100 * reduced / total) if total else 0
    header = (
        f"Alerts received: {total}\n"
        f"Unique alerts: {len(groups)}\n"
        f"Noise removed: {reduced} duplicates ({pct}%)\n"
    )
    if len(groups) > MAX_UNIQUE:
        header += f"Note: showing first {MAX_UNIQUE} unique alerts.\n"
    return header + "\n" + "\n".join(lines)
