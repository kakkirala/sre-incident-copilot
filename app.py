"""SRE Incident Copilot - web UI (port 5003).

- Paste an alert -> SAME agent from main.py diagnoses it.
- Approve / Edit / Escalate buttons: they only RECORD your decision.
  V1 rule: nothing on this page executes anything.
- Live metrics panel, laid out like the breadth screenshot Boss shared:
  metric names + values on the left, dotted trails over time on the right,
  HEALTHY vs BREACHING counts on top.
  IMPORTANT: we are NOT trading stocks. Every label here is an SRE metric
  collected live from this laptop: CPU, memory, disk read/write,
  and real-time network sent/received.
  Green dot = metric within its limit. Red dot = metric over its limit.
  Limits: CPU 80%, memory 85%, disk IO 100 MB/s (watch line for a laptop),
  network 10 MB/s (watch line, set low on purpose so a download trips it).
- Use case #4: paste an incident timeline -> blameless postmortem
  (status update + executive summary + action items, markdown).
  Saved to postmortem_output.md.
- Look: professional dashboard like the DebugBear screenshot Boss shared:
  dark blue sidebar, light background, white cards, big score numbers.

Port 5003 (5000 = Meal Planner, 5001 = Finance Planner, 5002 = MealBudget).
Needs: pip install psutil (add it to requirements.txt too).
"""

import time

import psutil
from flask import Flask, jsonify, render_template_string, request

from main import agent
from postmortem import generate_postmortem
from rca import analyze_rca
from runbook import build_runbook
from triage import triage_alerts

app = Flask(__name__)

_prev_io = psutil.disk_io_counters()
_prev_net = psutil.net_io_counters()
_prev_time = time.time()

PAGE = """
<!doctype html>
<html><head><meta charset="utf-8"><title>SRE Incident Copilot</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f2f5f8;color:#222}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:220px;background:#14365d;color:#fff;padding:20px 0}
.sidebar .logo{font-size:20px;font-weight:bold;padding:0 20px 22px}
.sidebar a{display:block;color:#cfe0f0;padding:12px 20px;text-decoration:none}
.sidebar a:hover{background:#1e4a7a;color:#fff}
.side-note{position:absolute;bottom:20px;left:20px;font-size:12px;color:#8fb0cc;line-height:1.6}
.main{margin-left:220px;padding:22px 26px}
.topbar{display:flex;justify-content:space-between;align-items:flex-start;gap:20px}
.topbar h1{margin:0 0 6px;color:#14365d}
.sub{margin:0;color:#555}
.scores{display:flex;gap:14px}
.score{background:#fff;border-radius:12px;padding:14px 26px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.score-num{font-size:36px;font-weight:bold}
.score-label{font-size:12px;color:#666;letter-spacing:1px}
.good{color:#1e7d32}.bad{color:#c62828}
.worst{color:#555;margin:14px 0 0}
.section{background:#fff;border-radius:12px;padding:20px 22px;margin-top:18px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.section h2{margin:0 0 10px 0;color:#14365d}
textarea{width:100%;height:90px;font-size:15px;padding:10px;border:1px solid #ccc;border-radius:10px}
textarea.tall{height:150px}
button{padding:11px 20px;margin-top:8px;cursor:pointer;font-size:15px;border:none;border-radius:10px}
.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:14px 0}
.metric-card{background:#f7f9fb;border:1px solid #e2e8f0;border-left:5px solid #1e7d32;border-radius:10px;padding:14px 16px}
.m-label{font-size:12px;color:#666;letter-spacing:1px}
.m-value{font-size:28px;font-weight:bold;margin:4px 0}
.m-limit{font-size:12px;color:#888}
canvas{width:100%;height:540px;border:1px solid #ddd;border-radius:10px}
pre{white-space:pre-wrap;background:#f7f9fb;border:1px solid #e2e8f0;padding:14px;border-radius:10px}
.banner{background:#fff8e1;border:1px solid #ffca28;border-radius:10px;padding:12px;margin-top:12px}
.approve{background:#1e7d32;color:#fff}
.escalate{background:#e65100;color:#fff}
.editbtn{background:#1565c0;color:#fff}
.pmbtn{background:#4a148c;color:#fff}
.primary{background:#14365d;color:#fff}
input[type=text]{padding:10px;font-size:15px;border:1px solid #ccc;border-radius:10px;width:300px}
.muted{color:#666;font-size:13px}
</style></head><body>
<div class="sidebar">
  <div class="logo">SRE Copilot</div>
  <a href="#top">Overview</a>
  <a href="#sec-diagnose">Diagnose</a>
  <a href="#sec-triage">Triage</a>
  <a href="#sec-rca">RCA</a>
  <a href="#sec-runbook">Runbook</a>
  <a href="#sec-postmortem">Postmortem</a>
  <a href="#sec-metrics">Live Metrics</a>
  <div class="side-note">Local &middot; Ollama llama3.2<br>V1: decisions recorded only,<br>nothing executes.</div>
</div>
<div class="main" id="top">
  <div class="topbar">
    <div>
      <h1>SRE Incident Copilot</h1>
      <p class="sub">Paste an alert. Get a cause + one safe step. Nothing runs until you approve.</p>
    </div>
    <div class="scores">
      <div class="score"><div class="score-num good"><span id="healthy">-</span></div><div class="score-label">HEALTHY</div></div>
      <div class="score"><div class="score-num bad"><span id="breach">-</span></div><div class="score-label">BREACHING</div></div>
    </div>
  </div>
  <p class="worst" id="worst"></p>

  <div class="section" id="sec-diagnose">
    <textarea id="alert" placeholder="Paste an alert here...">ALERT: payment-api p99 latency 8.2s (normal 0.4s), 5xx rate 12% for 15 minutes.
DB connection pool exhausted: 100/100 connections in use, 240 queries waiting.</textarea>
    <br><button class="primary" onclick="diagnose()">Diagnose</button>
    <pre id="result">Diagnosis will appear here.</pre>
    <div id="banner" class="banner" style="display:none"></div>
    <div style="margin-top:12px">
      <button class="approve" onclick="decide('approve')">Approve</button>
      <button class="escalate" onclick="decide('escalate')">Escalate</button>
      <input type="text" id="edited" placeholder="Type your edited step here">
      <button class="editbtn" onclick="decide('edit')">Edit &amp; Save</button>
    </div>
  </div>

  <div class="section" id="sec-triage">
    <h2>Alert triage (use case #1)</h2>
    <p>Paste a bunch of alerts, one per line. Duplicates are grouped first,
    then each unique alert gets a severity + owner team, worst first.</p>
    <textarea id="alerts" class="tall">ALERT: payment-api p99 latency 8.2s, 5xx rate 12%
ALERT: payment-api p99 latency 8.5s, 5xx rate 13%
ALERT: payment-api p99 latency 8.1s, 5xx rate 11%
ALERT: disk usage /var 92% on worker-3
ALERT: CPU usage 94% on worker-3
ALERT: disk usage /var 93% on worker-3
ALERT: checkout-service error rate 2% (normal 0.5%)</textarea>
    <br><button class="primary" onclick="makeTriage()">Triage alerts</button>
    <pre id="triage-result">Triage result will appear here. It is also saved to triage_output.md.</pre>
  </div>

  <div class="section" id="sec-rca">
    <h2>Root cause analysis (use case #2)</h2>
    <p>Paste what happened, the log lines from the incident window, and recent
    deploys. You get ranked causes with the log evidence behind each one.</p>
    <label class="muted">Incident (what, where, when)</label>
    <textarea id="rca-incident">payment-api p99 latency 8.2s (normal 0.4s), 5xx rate 12%, started 14:32, still ongoing at 14:45.</textarea>
    <label class="muted">Logs from the incident window</label>
    <textarea id="rca-logs" class="tall">14:32:10 payment-api ERROR HikariPool - Connection is not available, request timed out after 30000ms
14:32:15 payment-api WARN  DB pool active=100 idle=0 threads awaiting=240
14:32:40 payment-api ERROR checkout failed: could not get JDBC Connection
14:33:05 payment-api INFO  slow query: SELECT * FROM orders WHERE status='PENDING' took 28s
14:32:50 payment-api WARN  retry attempt 3/3 failed for order 88210</textarea>
    <label class="muted">Recent deploys / changes</label>
    <textarea id="rca-deploys">No deployments in the last 6 hours. Last deploy: payment-api v2.4.1 at 08:10, no issues reported.</textarea>
    <br><button class="primary" onclick="makeRCA()">Analyze root cause</button>
    <pre id="rca-result">RCA will appear here. It is also saved to rca_output.md.</pre>
  </div>

  <div class="section" id="sec-runbook">
    <h2>Guided remediation runbook (use case #3)</h2>
    <div class="banner">DRY-RUN ONLY: this page never executes a fix. The plan below is for
    your approval — Approve / Escalate only record your decision.</div>
    <p>Paste the incident and the confirmed cause. You get read-only checks
    first, one proposed fix, its risk, its rollback, and a dry-run preview.</p>
    <label class="muted">Incident</label>
    <textarea id="rb-incident">payment-api p99 latency 8.2s (normal 0.4s), 5xx rate 12%, DB pool 100/100 in use, 240 queries waiting.</textarea>
    <label class="muted">Confirmed cause (from RCA)</label>
    <textarea id="rb-cause">DB connection pool exhausted — idle sessions holding connections, plus one slow query (28s) on the orders table.</textarea>
    <br><button class="primary" onclick="makeRunbook()">Build runbook</button>
    <pre id="runbook-result">Runbook will appear here. It is also saved to runbook_output.md.</pre>
    <div id="banner-runbook" class="banner" style="display:none"></div>
    <div style="margin-top:12px">
      <button class="approve" onclick="decideRunbook('approve')">Approve plan</button>
      <button class="escalate" onclick="decideRunbook('escalate')">Escalate</button>
    </div>
  </div>

  <div class="section" id="sec-postmortem">
    <h2>Incident postmortem (use case #4)</h2>
    <p>Paste the incident timeline (or a Slack/Teams thread). You get a status update,
    an executive summary, and a blameless postmortem with action items.</p>
    <textarea id="timeline" class="tall">14:32 - Alert fired: payment-api p99 latency 8.2s (normal 0.4s), 5xx rate 12%.
14:35 - On-call engineer paged, acknowledged the alert.
14:40 - Checked dashboards: DB connection pool 100/100 in use, 240 queries waiting.
14:45 - No new deployment in the last 6 hours, ruled out a bad deploy.
14:50 - Killed long-running idle sessions and raised the pool temporarily.
15:02 - Latency back to 0.4s, 5xx rate back to 0%.
15:10 - Monitoring confirmed stable for 10 minutes, incident closed.</textarea>
    <br><button class="pmbtn" onclick="makePostmortem()">Generate postmortem</button>
    <pre id="postmortem">Postmortem will appear here. It is also saved to postmortem_output.md.</pre>
  </div>

  <div class="section" id="sec-metrics">
    <h2>Live metrics (this laptop)</h2>
    <div class="metric-grid">
      <div class="metric-card" id="card-cpu"><div class="m-label">CPU</div><div class="m-value"><span id="cpu">-</span>%</div><div class="m-limit">limit 80%</div></div>
      <div class="metric-card" id="card-mem"><div class="m-label">MEMORY</div><div class="m-value"><span id="mem">-</span>%</div><div class="m-limit">limit 85%</div></div>
      <div class="metric-card" id="card-read"><div class="m-label">DISK READ</div><div class="m-value"><span id="read">-</span> MB/s</div><div class="m-limit">limit 100 MB/s</div></div>
      <div class="metric-card" id="card-write"><div class="m-label">DISK WRITE</div><div class="m-value"><span id="write">-</span> MB/s</div><div class="m-limit">limit 100 MB/s</div></div>
      <div class="metric-card" id="card-sent"><div class="m-label">NET SENT</div><div class="m-value"><span id="sent">-</span> MB/s</div><div class="m-limit">limit 10 MB/s</div></div>
      <div class="metric-card" id="card-recv"><div class="m-label">NET RECEIVED</div><div class="m-value"><span id="recv">-</span> MB/s</div><div class="m-limit">limit 10 MB/s</div></div>
    </div>
    <p class="muted">Left = metric name + value + green/red bar. Right = dotted trail over time.
    Green dot = within limit, red dot = over limit.</p>
    <canvas id="breadth"></canvas>
  </div>
  <p class="muted">V1: decisions are recorded only — nothing executes.</p>
</div>
<script>
// One row per metric. value = current reading, scale = what "full" means,
// limit = where green turns red. All labels are metrics, not stocks.
const ROWS = [
  {key: 'cpu',   name: 'CPU',          unit: '%',    scale: 100, limit: 80},
  {key: 'mem',   name: 'MEMORY',       unit: '%',    scale: 100, limit: 85},
  {key: 'read',  name: 'DISK READ',    unit: ' MB/s', scale: 100, limit: 100},
  {key: 'write', name: 'DISK WRITE',   unit: ' MB/s', scale: 100, limit: 100},
  {key: 'sent',  name: 'NET SENT',     unit: ' MB/s', scale: 20,  limit: 10},
  {key: 'recv',  name: 'NET RECEIVED', unit: ' MB/s', scale: 20,  limit: 10},
];
const trail = {cpu: [], mem: [], read: [], write: [], sent: [], recv: []};
const MAX_POINTS = 60;  // 60 polls x 2s = last 2 minutes
function draw(){
  const c = document.getElementById('breadth');
  const W = c.clientWidth, H = 540;
  if(c.width !== W) c.width = W;
  c.height = H;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  const LABEL = 170, bandH = H / ROWS.length;
  ROWS.forEach((row, r) => {
    const top = r * bandH, bot = top + bandH;
    if(r % 2 === 0){ ctx.fillStyle = '#f7f9fb'; ctx.fillRect(0, top, W, bandH); }
    const pts = trail[row.key];
    const cur = pts.length ? pts[pts.length - 1] : 0;
    const breach = cur > row.limit;
    // Left: name + current value + green/red bar (like the screenshot's rows)
    ctx.fillStyle = '#222'; ctx.font = 'bold 14px Arial';
    ctx.fillText(row.name, 10, top + 24);
    ctx.fillStyle = breach ? '#c62828' : '#1e7d32'; ctx.font = '14px Arial';
    ctx.fillText(cur + row.unit, 10, top + 46);
    const barW = Math.min(140, 140 * cur / row.scale);
    ctx.fillRect(10, top + 54, barW, 8);
    ctx.fillStyle = '#666'; ctx.font = '11px Arial';
    ctx.fillText('limit ' + row.limit + row.unit, 10, top + 78);
    // Dashed limit line across this band
    const limitY = bot - 8 - (row.limit / row.scale) * (bandH - 16);
    ctx.strokeStyle = '#999'; ctx.setLineDash([5, 5]);
    ctx.beginPath(); ctx.moveTo(LABEL, limitY); ctx.lineTo(W - 5, limitY); ctx.stroke();
    ctx.setLineDash([]);
    // Dotted trail: one dot per poll, green = within limit, red = over
    pts.forEach((v, i) => {
      const x = LABEL + (pts.length === 1 ? 0 : i / (MAX_POINTS - 1)) * (W - LABEL - 10);
      const y = bot - 8 - Math.min(v / row.scale, 1) * (bandH - 16);
      ctx.fillStyle = v > row.limit ? '#c62828' : '#1e7d32';
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    });
    ctx.strokeStyle = '#ddd';
    ctx.beginPath(); ctx.moveTo(0, bot); ctx.lineTo(W, bot); ctx.stroke();
  });
}
function summarize(){
  let healthy = 0, worstName = '', worstPct = -1;
  ROWS.forEach(row => {
    const pts = trail[row.key];
    const cur = pts.length ? pts[pts.length - 1] : 0;
    const pct = cur / row.limit;
    if(cur <= row.limit) healthy++;
    if(pct > worstPct){ worstPct = pct; worstName = row.name + ' ' + cur + row.unit; }
  });
  document.getElementById('healthy').textContent = healthy;
  document.getElementById('breach').textContent = ROWS.length - healthy;
  document.getElementById('worst').textContent =
    (ROWS.length - healthy === 0) ? 'All metrics within limits' : 'HIGHEST LOAD: ' + worstName;
}
async function vitals(){
  const v = await (await fetch('/api/vitals')).json();
  document.getElementById('cpu').textContent = v.cpu;
  document.getElementById('mem').textContent = v.memory;
  document.getElementById('read').textContent = v.read_mbs;
  document.getElementById('write').textContent = v.write_mbs;
  document.getElementById('sent').textContent = v.sent_mbs;
  document.getElementById('recv').textContent = v.recv_mbs;
  const vals = {cpu: v.cpu, mem: v.memory, read: v.read_mbs, write: v.write_mbs, sent: v.sent_mbs, recv: v.recv_mbs};
  ROWS.forEach(row => {
    const card = document.getElementById('card-' + row.key);
    if(card) card.style.borderLeftColor = vals[row.key] > row.limit ? '#c62828' : '#1e7d32';
  });
  trail.cpu.push(v.cpu); trail.mem.push(v.memory);
  trail.read.push(v.read_mbs); trail.write.push(v.write_mbs);
  trail.sent.push(v.sent_mbs); trail.recv.push(v.recv_mbs);
  Object.keys(trail).forEach(k => { if(trail[k].length > MAX_POINTS) trail[k].shift(); });
  draw(); summarize();
}
async function diagnose(){
  document.getElementById('result').textContent = 'Thinking (local llama3.2)...';
  const form = new FormData();
  form.append('alert', document.getElementById('alert').value);
  const r = await (await fetch('/diagnose', {method:'POST', body: form})).json();
  if(r.error){ document.getElementById('result').textContent = r.error; return; }
  document.getElementById('result').textContent =
    'Service: ' + r.service + '\\nSymptom: ' + r.symptom +
    '\\nLikely cause: ' + r.likely_cause + '\\nReasoning:\\n' + r.reasoning +
    '\\nRecommended step: ' + r.recommended_step + '\\nCheck after:\\n' + r.check_after;
}
async function decide(choice){
  const form = new FormData();
  form.append('choice', choice);
  form.append('edited_step', document.getElementById('edited').value);
  const r = await (await fetch('/decision', {method:'POST', body: form})).json();
  const b = document.getElementById('banner');
  b.style.display = 'block';
  b.textContent = r.message;
  if(choice === 'edit' && document.getElementById('edited').value.trim()){
    document.getElementById('result').textContent +=
      '\\nEdited step: ' + document.getElementById('edited').value.trim();
  }
}
async function makePostmortem(){
  document.getElementById('postmortem').textContent = 'Writing (local llama3.2)...';
  const form = new FormData();
  form.append('timeline', document.getElementById('timeline').value);
  const r = await (await fetch('/postmortem', {method:'POST', body: form})).json();
  document.getElementById('postmortem').textContent = r.postmortem || r.error;
}
async function makeTriage(){
  document.getElementById('triage-result').textContent = 'Triaging (local llama3.2)...';
  const form = new FormData();
  form.append('alerts', document.getElementById('alerts').value);
  const r = await (await fetch('/triage', {method:'POST', body: form})).json();
  document.getElementById('triage-result').textContent = r.triage || r.error;
}
async function makeRCA(){
  document.getElementById('rca-result').textContent = 'Analyzing (local llama3.2)...';
  const form = new FormData();
  form.append('incident', document.getElementById('rca-incident').value);
  form.append('logs', document.getElementById('rca-logs').value);
  form.append('deploys', document.getElementById('rca-deploys').value);
  const r = await (await fetch('/rca', {method:'POST', body: form})).json();
  document.getElementById('rca-result').textContent = r.rca || r.error;
}
async function makeRunbook(){
  document.getElementById('runbook-result').textContent = 'Building (local llama3.2)...';
  const form = new FormData();
  form.append('incident', document.getElementById('rb-incident').value);
  form.append('cause', document.getElementById('rb-cause').value);
  const r = await (await fetch('/runbook', {method:'POST', body: form})).json();
  document.getElementById('runbook-result').textContent = r.runbook || r.error;
}
async function decideRunbook(choice){
  const form = new FormData();
  form.append('choice', choice);
  form.append('edited_step', '');
  const r = await (await fetch('/decision', {method:'POST', body: form})).json();
  const b = document.getElementById('banner-runbook');
  b.style.display = 'block';
  b.textContent = 'Runbook: ' + r.message;
}
vitals(); setInterval(vitals, 2000);
</script>
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/vitals")
def api_vitals():
    global _prev_io, _prev_net, _prev_time
    now = time.time()
    io = psutil.disk_io_counters()
    net = psutil.net_io_counters()
    elapsed = max(now - _prev_time, 0.1)
    # Disk and network counters only ever climb, so each graph needs the
    # *rate*: bytes since the last poll, divided by seconds since the last poll.
    read_mbs = round((io.read_bytes - _prev_io.read_bytes) / 1_000_000 / elapsed, 2)
    write_mbs = round((io.write_bytes - _prev_io.write_bytes) / 1_000_000 / elapsed, 2)
    sent_mbs = round((net.bytes_sent - _prev_net.bytes_sent) / 1_000_000 / elapsed, 2)
    recv_mbs = round((net.bytes_recv - _prev_net.bytes_recv) / 1_000_000 / elapsed, 2)
    _prev_io, _prev_net, _prev_time = io, net, now
    return jsonify(
        cpu=round(psutil.cpu_percent(interval=None), 1),
        memory=round(psutil.virtual_memory().percent, 1),
        read_mbs=read_mbs,
        write_mbs=write_mbs,
        sent_mbs=sent_mbs,
        recv_mbs=recv_mbs,
    )


@app.route("/diagnose", methods=["POST"])
def diagnose_route():
    alert = request.form.get("alert", "").strip()
    if not alert:
        return jsonify({"error": "Paste an alert first."})
    result = agent.invoke({"alert_text": alert})
    return jsonify(
        {
            "service": result["service"],
            "symptom": result["symptom"],
            "likely_cause": result["likely_cause"],
            "reasoning": result["reasoning"],
            "recommended_step": result["recommended_step"],
            "check_after": result["check_after"],
        }
    )


@app.route("/decision", methods=["POST"])
def decision_route():
    choice = request.form.get("choice", "")
    edited = request.form.get("edited_step", "").strip()
    if choice == "approve":
        msg = "Approved and recorded. V1 note: nothing was executed."
    elif choice == "escalate":
        msg = "Escalated and recorded. Next: hand this diagnosis to the next on-call engineer."
    elif choice == "edit" and edited:
        msg = "Step edited and recorded: " + edited
    elif choice == "edit":
        msg = "Edit was empty — original step kept."
    else:
        msg = "Unknown choice."
    return jsonify({"message": msg})


@app.route("/postmortem", methods=["POST"])
def postmortem_route():
    timeline = request.form.get("timeline", "").strip()
    if not timeline:
        return jsonify({"error": "Paste an incident timeline first."})
    text = generate_postmortem(timeline)
    with open("postmortem_output.md", "w", encoding="utf-8") as f:
        f.write(text)
    return jsonify({"postmortem": text})


@app.route("/triage", methods=["POST"])
def triage_route():
    alerts = request.form.get("alerts", "").strip()
    if not alerts:
        return jsonify({"error": "Paste alerts first (one per line)."})
    text = triage_alerts(alerts)
    with open("triage_output.md", "w", encoding="utf-8") as f:
        f.write(text)
    return jsonify({"triage": text})


@app.route("/rca", methods=["POST"])
def rca_route():
    incident = request.form.get("incident", "").strip()
    logs = request.form.get("logs", "").strip()
    deploys = request.form.get("deploys", "").strip()
    if not incident or not logs:
        return jsonify({"error": "Fill in the incident and the logs first."})
    text = analyze_rca(incident, logs, deploys or "None given.")
    with open("rca_output.md", "w", encoding="utf-8") as f:
        f.write(text)
    return jsonify({"rca": text})


@app.route("/runbook", methods=["POST"])
def runbook_route():
    incident = request.form.get("incident", "").strip()
    cause = request.form.get("cause", "").strip()
    if not incident or not cause:
        return jsonify({"error": "Fill in the incident and the confirmed cause first."})
    text = build_runbook(incident, cause)
    with open("runbook_output.md", "w", encoding="utf-8") as f:
        f.write(text)
    return jsonify({"runbook": text})


if __name__ == "__main__":
    app.run(port=5003)
